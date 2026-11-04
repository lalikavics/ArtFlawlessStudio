// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Lalikavics - ArtFlawless Studio
// ArtFlawless Studio window: a frameless WinForms window with an embedded WebView2 (Edge) browser.
// The Studio page draws its own title area and window buttons; this host does the window work
// (move, resize, minimise, maximise, close) and remembers the window position.
// Usage: ArtFlawlessHost.exe <url> <data folder> [icon]
// Exit codes: 0 = closed normally, 3 = WebView2 runtime missing, 4 = WebView2 failed to start (the launcher falls back to Edge).
// Written for the C# 5 compiler that ships with .NET Framework (PowerShell Add-Type).
//
// Two ways of showing the page (window-mode.txt in the data folder: "visual" or "window"; visual is the default):
//  - visual: the page is drawn into a DirectComposition visual of this window ("visual hosting"). During a resize drag every
//    step passes the new size on and waits for the next composed screen frame, so the window and the page change together.
//    The window forwards mouse input, the cursor and drag & drop to the page; the keyboard works by itself.
//  - window: the page runs in its own child window (WinForms WebView2 control). During a resize drag the new size is passed
//    on at most once per screen refresh. Used when visual hosting cannot start.
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using ComDataObject = System.Runtime.InteropServices.ComTypes.IDataObject;

public class AfHost : Form
{
    const int GRIP = 2;
    static readonly Color BG = Color.FromArgb(13, 15, 19);      // --bg
    static readonly Color LINE = Color.FromArgb(39, 44, 56);    // --line

    [DllImport("user32.dll")] static extern bool ReleaseCapture();
    [DllImport("user32.dll")] static extern IntPtr SetCapture(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr SetCursor(IntPtr c);
    [DllImport("user32.dll")] static extern IntPtr GetCapture();
    [DllImport("user32.dll")] static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(POINT p);
    [DllImport("user32.dll")] static extern IntPtr GetAncestor(IntPtr h, int flags);
    [DllImport("user32.dll")] static extern short GetKeyState(int vk);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll")] static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
    [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, int msg, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] static extern bool TrackMouseEvent(ref TRACKMOUSEEVENT e);
    [DllImport("user32.dll")] static extern IntPtr GetDC(IntPtr h);
    [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr h, IntPtr dc);
    [DllImport("gdi32.dll")] static extern int GetDeviceCaps(IntPtr dc, int i);
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr h, int attr, ref int val, int size);
    [DllImport("dwmapi.dll")] static extern int DwmFlush();
    [DllImport("dcomp.dll")] static extern int DCompositionCreateDevice2(IntPtr renderingDevice, ref Guid iid, out IntPtr device);
    [StructLayout(LayoutKind.Sequential)] struct TRACKMOUSEEVENT { public int cbSize; public int dwFlags; public IntPtr hwndTrack; public int dwHoverTime; }
    [StructLayout(LayoutKind.Sequential)] struct POINT { public int X, Y; }

    // COM calls by vtable slot (only these few are needed):
    // IDCompositionDevice: Commit 3, CreateTargetForHwnd 6, CreateVisual 7; IDCompositionTarget: SetRoot 3;
    // ICoreWebView2CompositionController3 (drag & drop, not wrapped by the .NET SDK): DragEnter 12, DragOver 14, Drop 15
    delegate int FnCommit(IntPtr self);
    delegate int FnCreateTarget(IntPtr self, IntPtr hwnd, int topmost, out IntPtr target);
    delegate int FnCreateVisual(IntPtr self, out IntPtr visual);
    delegate int FnSetRoot(IntPtr self, IntPtr visual);
    delegate int FnDragEnter(IntPtr self, IntPtr data, uint keys, POINT p, ref uint effect);
    delegate int FnDragOver(IntPtr self, uint keys, POINT p, ref uint effect);
    static T Slot<T>(IntPtr obj, int i) where T : class
    {
        IntPtr vt = Marshal.ReadIntPtr(obj);
        return Marshal.GetDelegateForFunctionPointer(Marshal.ReadIntPtr(vt, i * IntPtr.Size), typeof(T)) as T;
    }

    WebView2 web;                                   // window mode
    CoreWebView2CompositionController cc;           // visual mode
    IntPtr dcDevice, dcTarget, dcVisual, cc3;
    FnCommit commit;
    readonly string url, dataDir, stateFile, iconPath;
    readonly bool wantVisual;
    bool canClose, ready, lastMax, sizing, pending, tracking;
    DateTime askedAt = DateTime.MinValue;
    readonly Stopwatch since = Stopwatch.StartNew();
    double frameMs = 1000.0 / 60;
    Timer flush;
    string debugLog;   // window-debug.txt in the data folder: mouse capture and focus are written to window-debug.log
    void Dbg(string s) { if (debugLog == null) return; try { File.AppendAllText(debugLog, DateTime.Now.ToString("HH:mm:ss.fff") + " " + s + "\r\n"); } catch { } }
    static string Wnd(IntPtr h)
    {
        if (h == IntPtr.Zero) return "none";
        var b = new System.Text.StringBuilder(128); GetClassName(h, b, 128); int pid; GetWindowThreadProcessId(h, out pid);
        return "0x" + h.ToInt64().ToString("X") + " " + b + " pid " + pid;
    }

    CoreWebView2 Core { get { return cc != null ? cc.CoreWebView2 : (web != null ? web.CoreWebView2 : null); } }

    [STAThread]
    public static int Main(string[] args)
    {
        if (args.Length < 2) return 2;
        try { if (string.IsNullOrEmpty(CoreWebView2Environment.GetAvailableBrowserVersionString())) return 3; }
        catch { return 3; }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        var f = new AfHost(args[0], args[1], args.Length > 2 ? args[2] : null);
        Application.Run(f);
        return Environment.ExitCode;
    }

    public AfHost(string url, string dataDir, string icon)
    {
        this.url = url; this.dataDir = dataDir; iconPath = icon;
        stateFile = Path.Combine(dataDir, "window.txt");
        try { Directory.CreateDirectory(dataDir); } catch { }
        try { var mf = Path.Combine(dataDir, "window-mode.txt"); wantVisual = !(File.Exists(mf) && File.ReadAllText(mf).Trim().ToLowerInvariant() == "window"); }
        catch { wantVisual = true; }
        try { var df = Path.Combine(dataDir, "window-debug.txt"); if (File.Exists(df) && File.ReadAllText(df).Trim().ToLowerInvariant() == "on") debugLog = Path.Combine(dataDir, "window-debug.log"); } catch { }
        Text = "ArtFlawless Studio";
        FormBorderStyle = FormBorderStyle.None;
        BackColor = BG;
        DoubleBuffered = true;
        Padding = new Padding(GRIP);
        MinimumSize = new Size(960, 620);
        StartPosition = FormStartPosition.Manual;
        AllowDrop = true;
        if (icon != null && File.Exists(icon)) { try { Icon = new Icon(icon); } catch { } }
        IntPtr dc = GetDC(IntPtr.Zero); int hz = GetDeviceCaps(dc, 116); ReleaseDC(IntPtr.Zero, dc);   // VREFRESH
        if (hz > 1) frameMs = 1000.0 / hz;
        flush = new Timer(); flush.Interval = Math.Max(4, (int)frameMs); flush.Tick += delegate { if (pending) ApplyBounds(); };
        RestoreWindow();
        Load += OnLoadAsync;
        Resize += delegate
        {
            bool max = WindowState == FormWindowState.Maximized;
            int pad = max ? 0 : GRIP;
            if (Padding.All != pad) Padding = new Padding(pad);
            Invalidate(false);
            if (max != lastMax) { lastMax = max; SendState(); }
            // window mode: during a drag the size goes on at most once per screen refresh (the rest: next step, timer, end of drag)
            if (cc == null && sizing && since.Elapsed.TotalMilliseconds < frameMs) { pending = true; return; }
            ApplyBounds();
            // visual mode: wait for the frame with the new size to be composed, so every screen frame gets exactly one step
            if (cc != null && sizing) DwmFlush();
        };
        FormClosing += OnClosing;
        LocationChanged += delegate { if (WindowState == FormWindowState.Normal) FitMaxBounds(); if (cc != null) cc.NotifyParentWindowPositionChanged(); };
        HandleCreated += delegate { FitMaxBounds(); };
        DragEnter += OnDragEnter; DragOver += OnDragOver; DragLeave += delegate { if (cc != null) { try { cc.DragLeave(); } catch { } } }; DragDrop += OnDragDrop;
    }

    Rectangle PageRect()
    {
        int p = WindowState == FormWindowState.Maximized ? 0 : GRIP;
        return new Rectangle(p, p, Math.Max(0, ClientSize.Width - 2 * p), Math.Max(0, ClientSize.Height - 2 * p));
    }

    void ApplyBounds()
    {
        pending = false; since.Restart();
        if (cc != null) { cc.Bounds = PageRect(); commit(dcDevice); }
        else if (web != null) web.Bounds = PageRect();
    }

    protected override CreateParams CreateParams
    {
        get
        {
            var cp = base.CreateParams;
            // WS_THICKFRAME makes the window resizable (the sizing frame itself is removed in WM_NCCALCSIZE),
            // WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU: taskbar click, Aero Snap and Win+arrow keys work
            cp.Style |= 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000;
            cp.ClassStyle |= 0x00020000;           // CS_DROPSHADOW
            return cp;
        }
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        if (WindowState != FormWindowState.Maximized)
            using (var p = new Pen(LINE)) e.Graphics.DrawRectangle(p, 0, 0, ClientSize.Width - 1, ClientSize.Height - 1);
    }

    protected override void WndProc(ref Message m)
    {
        const int WM_NCHITTEST = 0x84, WM_NCCALCSIZE = 0x83, WM_NCACTIVATE = 0x86, WM_SETCURSOR = 0x20, WM_MOUSELEAVE = 0x2A3;
        if (m.Msg == WM_NCCALCSIZE && m.WParam != IntPtr.Zero) { m.Result = IntPtr.Zero; return; }   // no visible frame: all of it is page
        if (m.Msg == 0x231) { sizing = true; flush.Start(); }                                       // WM_ENTERSIZEMOVE
        if (m.Msg == 0x232) { sizing = false; flush.Stop(); if (pending) ApplyBounds(); }           // WM_EXITSIZEMOVE
        if (m.Msg == WM_NCACTIVATE)
        {
            // on focus change Windows would paint its grey frame line over the window edge; lParam -1 tells it to skip
            // that painting (the activation itself is handled normally) - the same way Chromium / Electron do it
            m.LParam = new IntPtr(-1);
            base.WndProc(ref m);
            return;
        }
        if (m.Msg == WM_NCHITTEST && WindowState == FormWindowState.Normal)
        {
            base.WndProc(ref m);
            long lp = m.LParam.ToInt64();
            Point p = PointToClient(new Point((short)(lp & 0xFFFF), (short)((lp >> 16) & 0xFFFF)));
            int w = ClientSize.Width, h = ClientSize.Height, g = GRIP + 3;
            bool l = p.X < g, r = p.X >= w - g, t = p.Y < g, b = p.Y >= h - g;
            int hit = 0;
            if (t && l) hit = 13; else if (t && r) hit = 14; else if (b && l) hit = 16; else if (b && r) hit = 17;
            else if (l) hit = 10; else if (r) hit = 11; else if (t) hit = 12; else if (b) hit = 15;
            if (hit == 0 && cc != null && OnCaption(p)) hit = 2;   // CSS app-region: drag areas of the page
            if (hit != 0) m.Result = (IntPtr)hit;
            return;
        }
        if (m.Msg == WM_NCHITTEST && cc != null && WindowState == FormWindowState.Maximized)
        {
            base.WndProc(ref m);
            long lp = m.LParam.ToInt64();
            if (OnCaption(PointToClient(new Point((short)(lp & 0xFFFF), (short)((lp >> 16) & 0xFFFF))))) m.Result = (IntPtr)2;
            return;
        }
        if (debugLog != null)
        {
            if (m.Msg == 0x215) Dbg("WM_CAPTURECHANGED -> " + Wnd(m.LParam) + " (this " + Wnd(Handle) + ", pid " + Process.GetCurrentProcess().Id + ")");
            else if (m.Msg == 0x07) Dbg("WM_SETFOCUS from " + Wnd(m.WParam));
            else if (m.Msg == 0x08) Dbg("WM_KILLFOCUS to " + Wnd(m.WParam));
            else if (m.Msg >= 0x201 && m.Msg <= 0x209) Dbg("mouse 0x" + m.Msg.ToString("X") + " capture=" + Wnd(GetCapture()));
            else if (m.Msg == 0x2A3) Dbg("WM_MOUSELEAVE");
            else if (m.Msg == 0x21) Dbg("WM_MOUSEACTIVATE");
        }
        if (cc != null)
        {
            if (m.Msg == WM_SETCURSOR && (m.LParam.ToInt64() & 0xFFFF) == 1 && cc.Cursor != IntPtr.Zero) { SetCursor(cc.Cursor); m.Result = (IntPtr)1; return; }   // HTCLIENT
            if (m.Msg >= 0x200 && m.Msg <= 0x20E) { Forward(ref m); return; }
            if (m.Msg == WM_MOUSELEAVE)
            {
                // Windows also sends this when a tooltip or the page's own helper window comes under the cursor; the page is
                // told only when the cursor has really left the window and no mouse button is held (a selection drag goes on)
                tracking = false;
                POINT cp; bool inside = GetCursorPos(out cp) && GetAncestor(WindowFromPoint(cp), 2) == Handle;   // GA_ROOT
                bool held = (GetKeyState(0x01) & 0x8000) != 0 || (GetKeyState(0x02) & 0x8000) != 0 || (GetKeyState(0x04) & 0x8000) != 0;
                if (!inside && !held) { try { cc.SendMouseInput(CoreWebView2MouseEventKind.Leave, CoreWebView2MouseEventVirtualKeys.None, 0, Point.Empty); } catch { } }
                return;
            }
        }
        base.WndProc(ref m);
    }

    bool OnCaption(Point client)
    {
        try { var r = PageRect(); return cc.GetNonClientRegionAtPoint(new Point(client.X - r.X, client.Y - r.Y)) == CoreWebView2NonClientRegionKind.Caption; }
        catch { return false; }
    }

    // visual mode: mouse messages of the window go to the page (in page coordinates)
    void Forward(ref Message m)
    {
        long lp = m.LParam.ToInt64(); Point p = new Point((short)(lp & 0xFFFF), (short)((lp >> 16) & 0xFFFF));
        uint data = 0;
        if (m.Msg == 0x20A || m.Msg == 0x20E) { p = PointToClient(p); data = (uint)((m.WParam.ToInt64() >> 16) & 0xFFFF); }   // wheel: screen coordinates
        if (m.Msg == 0x20B || m.Msg == 0x20C || m.Msg == 0x20D) data = (uint)((m.WParam.ToInt64() >> 16) & 0xFFFF);          // X buttons
        if (m.Msg == 0x201 || m.Msg == 0x204 || m.Msg == 0x207 || m.Msg == 0x20B) SetCapture(Handle);
        if (m.Msg == 0x202 || m.Msg == 0x205 || m.Msg == 0x208 || m.Msg == 0x20C) ReleaseCapture();
        if (m.Msg == 0x200 && !tracking)
        {
            var tme = new TRACKMOUSEEVENT(); tme.cbSize = Marshal.SizeOf(tme); tme.dwFlags = 2; tme.hwndTrack = Handle;   // TME_LEAVE
            tracking = TrackMouseEvent(ref tme);
        }
        var r = PageRect(); p.Offset(-r.X, -r.Y);
        try { cc.SendMouseInput((CoreWebView2MouseEventKind)m.Msg, (CoreWebView2MouseEventVirtualKeys)(m.WParam.ToInt64() & 0x7F), data, p); } catch { }
        m.Result = IntPtr.Zero;
    }

    // visual mode: drag & drop (files from Explorer, dragging inside the page) is passed to the page
    POINT DropPoint(DragEventArgs e) { var c = PointToClient(new Point(e.X, e.Y)); var r = PageRect(); var p = new POINT(); p.X = c.X - r.X; p.Y = c.Y - r.Y; return p; }
    static DragDropEffects Eff(uint v) { return (DragDropEffects)(int)v; }
    IntPtr ComData(DragEventArgs e) { try { return Marshal.GetComInterfaceForObject(e.Data, typeof(ComDataObject)); } catch { return IntPtr.Zero; } }
    void OnDragEnter(object s, DragEventArgs e)
    {
        if (cc3 == IntPtr.Zero) return; IntPtr d = ComData(e); if (d == IntPtr.Zero) return;
        uint eff = (uint)e.AllowedEffect;
        try { Slot<FnDragEnter>(cc3, 12)(cc3, d, (uint)e.KeyState, DropPoint(e), ref eff); e.Effect = Eff(eff); } catch { } finally { Marshal.Release(d); }
    }
    void OnDragOver(object s, DragEventArgs e)
    {
        if (cc3 == IntPtr.Zero) return; uint eff = (uint)e.AllowedEffect;
        try { Slot<FnDragOver>(cc3, 14)(cc3, (uint)e.KeyState, DropPoint(e), ref eff); e.Effect = Eff(eff); } catch { }
    }
    void OnDragDrop(object s, DragEventArgs e)
    {
        if (cc3 == IntPtr.Zero) return; IntPtr d = ComData(e); if (d == IntPtr.Zero) return;
        uint eff = (uint)e.AllowedEffect;
        try { Slot<FnDragEnter>(cc3, 15)(cc3, d, (uint)e.KeyState, DropPoint(e), ref eff); e.Effect = Eff(eff); } catch { } finally { Marshal.Release(d); }
    }

    protected override void OnActivated(EventArgs e) { base.OnActivated(e); if (cc != null) { try { cc.MoveFocus(CoreWebView2MoveFocusReason.Programmatic); } catch { } } }

    async void OnLoadAsync(object sender, EventArgs e)
    {
        CoreWebView2Environment env;
        try { env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(dataDir, "webview2")); }
        catch (Exception ex) { Fail(ex); return; }
        if (wantVisual)
        {
            try { await StartVisual(env); }
            catch
            {
                // visual hosting could not start: the normal child window is used instead
                try { if (cc != null) cc.Close(); } catch { }
                cc = null;
            }
        }
        if (cc == null)
        {
            try
            {
                web = new WebView2();
                web.DefaultBackgroundColor = BG;
                web.Bounds = PageRect();
                Controls.Add(web);
                await web.EnsureCoreWebView2Async(env);
            }
            catch (Exception ex) { Fail(ex); return; }
        }
        try { File.WriteAllText(Path.Combine(dataDir, "window-mode-used.txt"), (cc != null ? "visual" : "window") + (cc != null && cc3 == IntPtr.Zero ? " (no drag & drop)" : "")); } catch { }
        var core = Core;
        var st = core.Settings;
        // newer runtimes: CSS "app-region: drag" areas act as the title bar (move, double-click, snap)
        try { var pi = st.GetType().GetProperty("IsNonClientRegionSupportEnabled"); if (pi != null) pi.SetValue(st, true, null); } catch { }
        st.IsStatusBarEnabled = false;
        core.WebMessageReceived += OnMessage;
        core.NewWindowRequested += OnNewWindow;
        core.NavigationCompleted += delegate { ready = true; SendState(); };
        core.ContextMenuRequested += OnContextMenu;
        if (debugLog == null) { try { st.AreDevToolsEnabled = false; } catch { } }   // no F12 / Inspect in normal use
        core.Navigate(url);
    }

    async System.Threading.Tasks.Task StartVisual(CoreWebView2Environment env)
    {
        Guid iid = new Guid("C37EA93A-E7AA-450D-B16F-9746CB0407F3");      // IDCompositionDevice
        int hr = DCompositionCreateDevice2(IntPtr.Zero, ref iid, out dcDevice); if (hr != 0) throw new Exception("dcomp " + hr);
        hr = Slot<FnCreateTarget>(dcDevice, 6)(dcDevice, Handle, 1, out dcTarget); if (hr != 0) throw new Exception("target " + hr);   // above the window's own dark background
        hr = Slot<FnCreateVisual>(dcDevice, 7)(dcDevice, out dcVisual); if (hr != 0) throw new Exception("visual " + hr);
        hr = Slot<FnSetRoot>(dcTarget, 3)(dcTarget, dcVisual); if (hr != 0) throw new Exception("root " + hr);
        commit = Slot<FnCommit>(dcDevice, 3);
        cc = await env.CreateCoreWebView2CompositionControllerAsync(Handle);
        cc.RootVisualTarget = Marshal.GetObjectForIUnknown(dcVisual);
        cc.DefaultBackgroundColor = BG;
        cc.Bounds = PageRect();
        cc.CursorChanged += delegate { if (cc.Cursor != IntPtr.Zero) SetCursor(cc.Cursor); };
        cc.GotFocus += delegate { Dbg("webview GotFocus"); }; cc.LostFocus += delegate { Dbg("webview LostFocus"); };
        commit(dcDevice);
        try
        {
            var f = typeof(CoreWebView2Controller).GetField("_rawNative", BindingFlags.NonPublic | BindingFlags.Instance);
            object raw = f != null ? f.GetValue(cc) : null;
            if (raw != null)
            {
                IntPtr unk = Marshal.GetIUnknownForObject(raw); Guid i3 = new Guid("9570570e-4d76-4361-9ee1-f04d0dbdfb1e");
                IntPtr p3; if (Marshal.QueryInterface(unk, ref i3, out p3) == 0) cc3 = p3;
                Marshal.Release(unk);
            }
        }
        catch { cc3 = IntPtr.Zero; }   // no drag & drop into the page, everything else works
    }

    // right-click menu: only in text fields (cut, copy, paste, select all) and on selected text (copy); nowhere else
    void OnContextMenu(object sender, CoreWebView2ContextMenuRequestedEventArgs e)
    {
        try
        {
            var t = e.ContextMenuTarget; bool edit = t.IsEditable, sel = t.HasSelection;
            if (!edit && !sel) { e.Handled = true; return; }
            var keep = edit ? new[] { "cut", "copy", "paste", "selectAll" } : new[] { "copy" };
            var items = e.MenuItems;
            for (int i = items.Count - 1; i >= 0; i--)
            {
                var it = items[i]; bool ok = false;
                foreach (var k in keep) if (string.Equals(it.Name, k, StringComparison.OrdinalIgnoreCase)) ok = true;
                if (!ok) items.RemoveAt(i);
            }
            if (items.Count == 0) e.Handled = true;
        }
        catch { }
    }

    void Fail(Exception ex)
    {
        MessageBox.Show("The Studio window could not start (WebView2): " + ex.Message + "\n\nThe Studio will open in Microsoft Edge instead.",
            "ArtFlawless Studio", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        Environment.ExitCode = 4; canClose = true; Close();
    }

    void OnMessage(object sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        string m;
        try { m = e.TryGetWebMessageAsString(); } catch { return; }
        if (m == "min") WindowState = FormWindowState.Minimized;
        else if (m == "max") ToggleMax();
        else if (m == "close") { canClose = true; Close(); }
        else if (m.StartsWith("resize:") && WindowState == FormWindowState.Normal)
        {
            int ht;   // edge strips drawn by the page: start the normal Windows resize from that edge
            if (int.TryParse(m.Substring(7), out ht) && ht >= 10 && ht <= 17) { ReleaseCapture(); SendMessage(Handle, 0xA1, (IntPtr)ht, IntPtr.Zero); }
        }
        else if (m == "drag") { ReleaseCapture(); SendMessage(Handle, 0xA1, (IntPtr)2, IntPtr.Zero); }   // WM_NCLBUTTONDOWN on the caption
    }

    void FitMaxBounds()
    {
        var s = Screen.FromHandle(Handle);
        var wa = s.WorkingArea;   // maximised = the working area of this monitor, so the taskbar stays visible
        MaximizedBounds = new Rectangle(wa.X - s.Bounds.X, wa.Y - s.Bounds.Y, wa.Width, wa.Height);
    }

    void ToggleMax()
    {
        if (WindowState == FormWindowState.Maximized) { WindowState = FormWindowState.Normal; return; }
        FitMaxBounds();
        WindowState = FormWindowState.Maximized;
    }

    void SendState()
    {
        var core = Core;
        if (!ready || core == null) return;
        try { core.ExecuteScriptAsync("window.afHostState && window.afHostState('" + (WindowState == FormWindowState.Maximized ? "max" : "normal") + "')"); } catch { }
    }

    async void OnClosing(object sender, FormClosingEventArgs e)
    {
        var core = Core;
        if (canClose || !ready || core == null) { SaveWindow(); return; }
        // Alt+F4 or the taskbar: let the page ask (a generation may be running); a second try after 4 s closes anyway
        if ((DateTime.Now - askedAt).TotalSeconds < 4 && askedAt != DateTime.MinValue) { SaveWindow(); return; }
        e.Cancel = true; askedAt = DateTime.Now;
        string r = null;
        try { r = await core.ExecuteScriptAsync("(window.afHostClose ? (window.afHostClose(), 'handled') : 'none')"); } catch { }
        if (r == null || r.IndexOf("handled", StringComparison.Ordinal) < 0) { canClose = true; Close(); }
    }

    async void OnNewWindow(object sender, CoreWebView2NewWindowRequestedEventArgs e)
    {
        Uri u;
        if (Uri.TryCreate(e.Uri, UriKind.Absolute, out u) && (u.Scheme == "http" || u.Scheme == "https") && !u.IsLoopback)
        {
            e.Handled = true;   // licence pages and other web links: the normal browser
            try { Process.Start(new ProcessStartInfo(e.Uri) { UseShellExecute = true }); } catch { }
            return;
        }
        // local pages (the ComfyUI copy): our own window, so the Studio can still fill it through window.open()
        var d = e.GetDeferral();
        try
        {
            var pop = new AfPopup(iconPath);
            pop.Show();
            await pop.Web.EnsureCoreWebView2Async(Core.Environment);
            e.NewWindow = pop.Web.CoreWebView2;
            e.Handled = true;
        }
        catch { }
        finally { d.Complete(); }
    }

    void RestoreWindow()
    {
        var wa = Screen.PrimaryScreen.WorkingArea;
        int w = Math.Min(1500, wa.Width - 40), h = Math.Min(950, wa.Height - 40);
        Bounds = new Rectangle(wa.X + (wa.Width - w) / 2, wa.Y + (wa.Height - h) / 2, w, h);
        try
        {
            if (!File.Exists(stateFile)) return;
            var p = File.ReadAllText(stateFile).Trim().Split(',');
            var r = new Rectangle(int.Parse(p[0]), int.Parse(p[1]), int.Parse(p[2]), int.Parse(p[3]));
            bool visible = false;
            foreach (var s in Screen.AllScreens) if (s.WorkingArea.IntersectsWith(new Rectangle(r.X + 40, r.Y + 10, Math.Max(1, r.Width - 80), 40))) visible = true;
            if (visible && r.Width >= 600 && r.Height >= 400) Bounds = r;
            if (p.Length > 4 && p[4] == "1") Shown += delegate { ToggleMax(); };
        }
        catch { }
    }

    void SaveWindow()
    {
        try
        {
            var r = WindowState == FormWindowState.Normal ? Bounds : RestoreBounds;
            File.WriteAllText(stateFile, r.X + "," + r.Y + "," + r.Width + "," + r.Height + "," + (WindowState == FormWindowState.Maximized ? "1" : "0"));
        }
        catch { }
    }

    internal static void DarkTitle(IntPtr h)
    {
        int one = 1;
        try { DwmSetWindowAttribute(h, 20, ref one, 4); DwmSetWindowAttribute(h, 19, ref one, 4); } catch { }
    }
}

// a normal window for pages the Studio opens (the ComfyUI copy)
public class AfPopup : Form
{
    public readonly WebView2 Web;
    public AfPopup(string icon)
    {
        Text = "ArtFlawless Studio - ComfyUI";
        BackColor = Color.FromArgb(13, 15, 19);
        var wa = Screen.PrimaryScreen.WorkingArea;
        int w = Math.Min(1600, wa.Width - 60), h = Math.Min(1000, wa.Height - 60);
        StartPosition = FormStartPosition.Manual;
        Bounds = new Rectangle(wa.X + (wa.Width - w) / 2 + 30, wa.Y + (wa.Height - h) / 2 + 20, w, h);
        if (icon != null && File.Exists(icon)) { try { Icon = new Icon(icon); } catch { } }
        Web = new WebView2();
        Web.Dock = DockStyle.Fill;
        Web.DefaultBackgroundColor = BackColor;
        Controls.Add(Web);
        Web.CoreWebView2InitializationCompleted += delegate
        {
            if (Web.CoreWebView2 == null) return;
            Web.CoreWebView2.DocumentTitleChanged += delegate { Text = Web.CoreWebView2.DocumentTitle; };
            Web.CoreWebView2.WindowCloseRequested += delegate { Close(); };
        };
    }
    protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); AfHost.DarkTitle(Handle); }
}
