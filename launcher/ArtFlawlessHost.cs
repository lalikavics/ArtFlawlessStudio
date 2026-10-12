// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Lalikavics - ArtFlawless Studio
// ArtFlawless Studio window: a frameless WinForms window with an embedded WebView2 (Edge) browser.
// The Studio page draws its own title area and window buttons; this host does the window work
// (move, resize, minimise, maximise, close) and remembers the window position.
// Usage: ArtFlawlessHost.exe <url> <data folder> [icon]
// Exit codes: 0 = closed normally, 3 = WebView2 runtime missing, 4 = WebView2 failed to start (the launcher falls back to Edge).
// Written for the C# 5 compiler that ships with .NET Framework (PowerShell Add-Type).
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

public class AfHost : Form
{
    const int GRIP = 2;
    static readonly Color BG = Color.FromArgb(13, 15, 19);      // --bg
    static readonly Color LINE = Color.FromArgb(39, 44, 56);    // --line

    [DllImport("user32.dll")] static extern bool ReleaseCapture();
    [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, int msg, IntPtr w, IntPtr l);
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr h, int attr, ref int val, int size);

    readonly WebView2 web;
    readonly string url, dataDir, stateFile, iconPath;
    bool canClose, ready;
    DateTime askedAt = DateTime.MinValue;

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
        Text = "ArtFlawless Studio";
        FormBorderStyle = FormBorderStyle.None;
        BackColor = BG;
        DoubleBuffered = true;
        Padding = new Padding(GRIP);
        MinimumSize = new Size(960, 620);
        StartPosition = FormStartPosition.Manual;
        if (icon != null && File.Exists(icon)) { try { Icon = new Icon(icon); } catch { } }
        RestoreWindow();
        web = new WebView2();
        web.Dock = DockStyle.Fill;
        web.DefaultBackgroundColor = BG;
        Controls.Add(web);
        Load += OnLoadAsync;
        Resize += delegate { Padding = new Padding(WindowState == FormWindowState.Maximized ? 0 : GRIP); Invalidate(); SendState(); };
        FormClosing += OnClosing;
        LocationChanged += delegate { if (WindowState == FormWindowState.Normal) FitMaxBounds(); };
        HandleCreated += delegate { FitMaxBounds(); };
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
        const int WM_NCHITTEST = 0x84, WM_NCCALCSIZE = 0x83;
        if (m.Msg == WM_NCCALCSIZE && m.WParam != IntPtr.Zero) { m.Result = IntPtr.Zero; return; }   // no visible frame: all of it is page
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
            if (hit != 0) m.Result = (IntPtr)hit;
            return;
        }
        base.WndProc(ref m);
    }

    async void OnLoadAsync(object sender, EventArgs e)
    {
        try
        {
            var env = await CoreWebView2Environment.CreateAsync(null, Path.Combine(dataDir, "webview2"));
            await web.EnsureCoreWebView2Async(env);
            var core = web.CoreWebView2;
            var st = core.Settings;
            // newer runtimes: CSS "app-region: drag" areas act as the title bar (move, double-click, snap)
            try { var pi = st.GetType().GetProperty("IsNonClientRegionSupportEnabled"); if (pi != null) pi.SetValue(st, true, null); } catch { }
            st.IsStatusBarEnabled = false;
            core.WebMessageReceived += OnMessage;
            core.NewWindowRequested += OnNewWindow;
            core.NavigationCompleted += delegate { ready = true; SendState(); };
            web.Source = new Uri(url);
        }
        catch (Exception ex)
        {
            MessageBox.Show("The Studio window could not start (WebView2): " + ex.Message + "\n\nThe Studio will open in Microsoft Edge instead.",
                "ArtFlawless Studio", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            Environment.ExitCode = 4; canClose = true; Close();
        }
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
        if (!ready || web.CoreWebView2 == null) return;
        try { web.CoreWebView2.ExecuteScriptAsync("window.afHostState && window.afHostState('" + (WindowState == FormWindowState.Maximized ? "max" : "normal") + "')"); } catch { }
    }

    async void OnClosing(object sender, FormClosingEventArgs e)
    {
        if (canClose || !ready || web.CoreWebView2 == null) { SaveWindow(); return; }
        // Alt+F4 or the taskbar: let the page ask (a generation may be running); a second try after 4 s closes anyway
        if ((DateTime.Now - askedAt).TotalSeconds < 4 && askedAt != DateTime.MinValue) { SaveWindow(); return; }
        e.Cancel = true; askedAt = DateTime.Now;
        string r = null;
        try { r = await web.CoreWebView2.ExecuteScriptAsync("(window.afHostClose ? (window.afHostClose(), 'handled') : 'none')"); } catch { }
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
            await pop.Web.EnsureCoreWebView2Async(web.CoreWebView2.Environment);
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
