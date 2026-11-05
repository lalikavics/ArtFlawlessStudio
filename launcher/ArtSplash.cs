// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Lalikavics - ArtFlawless Studio
// The start / setup window: a rounded panel of the Studio (drawn in splash-bg.png) with the logo, a turning ring and a list of
// what is happening. Finished tasks slide up with a tick, the current one comes in at the bottom with a small turning dash.
// It is a layered window (per-pixel alpha: smooth corners and a real soft shadow, no Windows frame) on its own thread, so it
// keeps turning while the PowerShell script waits. The scripts load it with Add-Type and call the static methods.
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

public static class ArtSplash
{
    // ---- layout in logical pixels (the background image is drawn at 2x: 880 x 472)
    const int W = 440, H = 236;                 // window incl. the shadow margin
    const int CX = 20, CY = 16, CW = 400, CH = 200;   // the panel
    const float LOG_TOP = CY + 85 + 6, LOG_BOTTOM = CY + CH - 12, LINE = 19f, LOG_LEFT = CX + 28, LOG_RIGHT = CX + CW - 22;
    const float FADE = 34f;                     // the upper lines fade out under the divider

    class Line { public string Text; public int Kind; public float Alpha; public double Born; }
    // Kind: 0 = done (tick), 1 = current (turning dash), 2 = note (small, no mark), 3 = error (!)

    static readonly object Lk = new object();
    static readonly List<Line> Lines = new List<Line>();
    static float scrollOff;                     // > 0 right after a new line: everything slides up from here to 0
    static string title = "ArtFlawless Studio";
    static bool spinning = true, topMost = true;
    static Thread thread;
    static SplashForm form;
    static Bitmap bg;
    static Icon icon;
    static readonly System.Diagnostics.Stopwatch Clock = System.Diagnostics.Stopwatch.StartNew();
    static ManualResetEvent ready = new ManualResetEvent(false);

    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();

    public static void Start(string bgPath, string iconPath, bool onTop)
    {
        if (thread != null) return;
        topMost = onTop;
        try { SetProcessDPIAware(); } catch { }
        try { bg = new Bitmap(bgPath); } catch { bg = null; }
        try { if (!string.IsNullOrEmpty(iconPath)) icon = new Icon(iconPath); } catch { icon = null; }
        thread = new Thread(Run);
        thread.SetApartmentState(ApartmentState.STA);
        thread.IsBackground = true;
        thread.Start();
        ready.WaitOne(5000);
    }

    static void Run()
    {
        try {
            Application.EnableVisualStyles();
            form = new SplashForm();
            form.Load += (s, e) => ready.Set();
            Application.Run(form);
        } catch { ready.Set(); }
    }

    static double Now { get { return Clock.Elapsed.TotalSeconds; } }

    // the current task (the earlier current one becomes a finished line)
    public static void Step(string text) { lock (Lk) { Finish(null); Push(text, 1); } }
    // changes the text of the current task without a new line (download progress, counters)
    public static void Update(string text) { lock (Lk) { var c = Cur(); if (c != null) c.Text = text; else Push(text, 1); } }
    // the current task is finished: it gets a tick (with a new text when given)
    public static void Done(string text) { lock (Lk) { if (!Finish(text) && text != null) Push(text, 0); } }
    public static void Note(string text) { lock (Lk) { Push(text, 2); } }
    public static void Error(string text) { lock (Lk) { Finish(null); Push(text, 3); spinning = false; } }
    // the current task failed, but the work goes on (the ring keeps turning)
    public static void Fail(string text) { lock (Lk) { var c = Cur(); if (c != null) { c.Kind = 3; if (text != null) c.Text = text; } else Push(text, 3); } }
    public static void SetTitle(string text) { lock (Lk) { title = text; } }

    public static void Close()
    {
        var f = form;
        if (f != null) { try { f.BeginInvoke(new Action(() => f.Close())); } catch { } }
        if (thread != null) thread.Join(2000);
        thread = null; form = null;
    }

    // a message on top of the window (the scripts' questions and errors), returns true for OK / Yes
    public static bool Ask(string text, string caption, bool yesNo)
    {
        var f = form; DialogResult r = DialogResult.None;
        Func<DialogResult> show = () => MessageBox.Show(f, text, caption, yesNo ? MessageBoxButtons.OKCancel : MessageBoxButtons.OK,
            yesNo ? MessageBoxIcon.Information : MessageBoxIcon.Warning);
        try { r = (f != null && f.IsHandleCreated) ? (DialogResult)f.Invoke(show) : MessageBox.Show(text, caption); } catch { r = MessageBox.Show(text, caption); }
        return r == DialogResult.OK || r == DialogResult.Yes;
    }

    static Line Cur() { for (int i = Lines.Count - 1; i >= 0; i--) if (Lines[i].Kind == 1) return Lines[i]; return null; }
    static bool Finish(string text)
    {
        var c = Cur(); if (c == null) return false;
        c.Kind = 0; if (text != null) c.Text = text; return true;
    }
    static void Push(string text, int kind)
    {
        // a note stays at the bottom, under the current line (a new step goes in above it)
        var notes = kind == 2 ? new List<Line>() : Lines.FindAll(l => l.Kind == 2);
        Lines.RemoveAll(l => notes.Contains(l));
        Lines.Add(new Line { Text = text ?? "", Kind = kind, Alpha = 0, Born = Now });
        Lines.AddRange(notes);
        scrollOff += LINE;
        while (Lines.Count > 12) Lines.RemoveAt(0);
    }

    // ------------------------------------------------------------------ drawing
    static readonly Color Yellow = Color.FromArgb(242, 184, 75);
    static Font fTitle, fLine, fNote;

    static void Fonts(float s)
    {
        if (fTitle != null) return;
        fTitle = Mk(new[] { "Segoe UI Semibold", "Segoe UI" }, 18f * s, FontStyle.Regular);
        fLine = Mk(new[] { "Segoe UI" }, 12f * s, FontStyle.Regular);      // like the grey texts of the Studio's inner panels
        fNote = Mk(new[] { "Segoe UI" }, 12f * s, FontStyle.Regular);
    }
    static Font Mk(string[] names, float px, FontStyle st)
    {
        foreach (var n in names) { try { var f = new Font(n, px, st, GraphicsUnit.Pixel); if (f.Name == n) return f; f.Dispose(); } catch { } }
        return new Font(FontFamily.GenericSansSerif, px, st, GraphicsUnit.Pixel);
    }

    static Bitmap Render(float s, double t)
    {
        int bw = (int)Math.Round(W * s), bh = (int)Math.Round(H * s);
        var bmp = new Bitmap(bw, bh, PixelFormat.Format32bppPArgb);
        using (var g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias; g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality; g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;
            g.CompositingQuality = CompositingQuality.HighQuality;
            g.Clear(Color.Transparent);
            if (bg != null) g.DrawImage(bg, new Rectangle(0, 0, bw, bh));
            Fonts(s);

            string ti; bool spin; List<Line> ls; float off;
            lock (Lk) { ti = title; spin = spinning; ls = new List<Line>(Lines); off = scrollOff; }

            // title (left of the ring, right of the logo that is in the background)
            using (var b = new SolidBrush(Color.White))
                g.DrawString(ti, fTitle, b, new PointF((CX + 89) * s, (CY + 42) * s - fTitle.GetHeight() / 2f - 1 * s));

            // the turning ring at the right, like the generation spinner of the viewer
            float rx = (CX + CW - 24 - 22) * s, ry = (CY + 42 - 11) * s, rd = 22 * s, pw = 2.5f * s;
            var rr = new RectangleF(rx + pw / 2, ry + pw / 2, rd - pw, rd - pw);
            if (spin) {
                using (var p = new Pen(Color.FromArgb(56, Yellow), pw)) g.DrawEllipse(p, rr);
                using (var p = new Pen(Yellow, pw)) { p.StartCap = LineCap.Flat; p.EndCap = LineCap.Flat;
                    g.DrawArc(p, rr, (float)((t / 0.9 * 360.0) % 360.0) - 90f, 90f); }
            } else {
                using (var p = new Pen(Color.FromArgb(150, 255, 157, 138), pw)) g.DrawEllipse(p, rr);
            }

            // the list: the newest line at the bottom, the older ones above it, sliding up after a new one came
            var clip = new RectangleF(CX * s, LOG_TOP * s, CW * s, (LOG_BOTTOM - LOG_TOP + 2) * s);
            g.SetClip(clip);
            float y = LOG_BOTTOM - LINE + off;
            for (int i = ls.Count - 1; i >= 0; i--, y -= LINE)
            {
                var l = ls[i];
                if (y + LINE < LOG_TOP) break;
                float a = Math.Min(1f, l.Alpha);
                float fade = Math.Max(0f, Math.Min(1f, (y + LINE * 0.6f - LOG_TOP) / FADE));
                a *= fade; if (a <= 0.01f) continue;
                Color tc = l.Kind == 1 ? Color.White : l.Kind == 3 ? Color.FromArgb(255, 157, 138)
                         : l.Kind == 2 ? Color.FromArgb(112, 112, 112) : Color.FromArgb(149, 149, 149);   // #959595 = the panels' grey text
                var font = l.Kind == 2 ? fNote : fLine;
                float ty = (y + (LINE - font.GetHeight() / s) / 2f) * s;
                float tx = (LOG_LEFT + 16) * s;
                // the mark in front
                float mx = LOG_LEFT * s + 4 * s, my = (y + LINE / 2f) * s;
                if (l.Kind == 0) using (var p = new Pen(Color.FromArgb((int)(a * 255), 149, 149, 149), 1.4f * s)) {
                    g.DrawLines(p, new[] { new PointF(mx - 4 * s, my), new PointF(mx - 1.3f * s, my + 2.8f * s), new PointF(mx + 4 * s, my - 3.2f * s) }); }
                else if (l.Kind == 1) using (var p = new Pen(Color.FromArgb((int)(a * 255), Yellow), 1.8f * s)) {
                    p.StartCap = LineCap.Round; p.EndCap = LineCap.Round;
                    double ang = t / 0.8 * Math.PI * 2; float r = 4.2f * s;
                    float dx = (float)(Math.Cos(ang) * r), dy = (float)(Math.Sin(ang) * r);
                    g.DrawLine(p, mx - dx, my - dy, mx + dx, my + dy); }
                else if (l.Kind == 3) using (var b = new SolidBrush(Color.FromArgb((int)(a * 255), tc))) {
                    g.DrawString("!", fLine, b, mx - 3 * s, ty); }
                var rect = new RectangleF(tx, ty, (LOG_RIGHT * s) - tx, font.GetHeight() + 4 * s);
                using (var sf = new StringFormat(StringFormatFlags.NoWrap) { Trimming = StringTrimming.EllipsisCharacter })
                using (var b = new SolidBrush(Color.FromArgb((int)(a * 255), tc)))
                    g.DrawString(l.Text, font, b, rect, sf);
            }
            g.ResetClip();
        }
        return bmp;
    }

    // the animation clock: lines fade in, the list slides up (eased)
    static void Tick(double dt)
    {
        lock (Lk)
        {
            foreach (var l in Lines) if (l.Alpha < 1) l.Alpha = Math.Min(1f, l.Alpha + (float)(dt / 0.25));
            if (scrollOff > 0) { scrollOff -= (float)Math.Max(dt * 60, scrollOff * dt * 12); if (scrollOff < 0) scrollOff = 0; }
        }
    }

    // ------------------------------------------------------------------ the layered window
    class SplashForm : Form
    {
        readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
        double last;
        float scale = 1f;

        public SplashForm()
        {
            FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = true; StartPosition = FormStartPosition.Manual;
            Text = "ArtFlawless Studio"; TopMost = topMost;
            if (icon != null) Icon = icon;
            using (var g = CreateGraphics()) scale = Math.Max(1f, g.DpiX / 96f);
            var wa = Screen.PrimaryScreen.WorkingArea;
            Size = new Size((int)Math.Round(W * scale), (int)Math.Round(H * scale));
            Location = new Point(wa.Left + (wa.Width - Width) / 2, wa.Top + (wa.Height - Height) / 2);
            timer.Interval = 33; timer.Tick += (s, e) => Frame();
            Load += (s, e) => { last = Now; Frame(); timer.Start(); };
            FormClosed += (s, e) => timer.Stop();
        }

        protected override CreateParams CreateParams
        {
            get { var cp = base.CreateParams; cp.ExStyle |= 0x00080000; /* WS_EX_LAYERED */ return cp; }
        }

        // the window can be moved by dragging it anywhere
        protected override void WndProc(ref Message m)
        {
            if (m.Msg == 0x84) { m.Result = (IntPtr)2; return; }   // WM_NCHITTEST -> HTCAPTION
            base.WndProc(ref m);
        }

        void Frame()
        {
            double t = Now; Tick(Math.Min(0.1, t - last)); last = t;
            using (var bmp = Render(scale, t)) Apply(bmp);
        }

        void Apply(Bitmap bmp)
        {
            IntPtr screen = GetDC(IntPtr.Zero), mem = CreateCompatibleDC(screen), hb = IntPtr.Zero, old = IntPtr.Zero;
            try {
                hb = bmp.GetHbitmap(Color.FromArgb(0)); old = SelectObject(mem, hb);
                var size = new SIZE { cx = bmp.Width, cy = bmp.Height };
                var src = new POINT { x = 0, y = 0 };
                var pos = new POINT { x = Left, y = Top };
                var bf = new BLENDFUNCTION { BlendOp = 0, BlendFlags = 0, SourceConstantAlpha = 255, AlphaFormat = 1 };
                UpdateLayeredWindow(Handle, screen, ref pos, ref size, mem, ref src, 0, ref bf, 2 /* ULW_ALPHA */);
            } finally {
                ReleaseDC(IntPtr.Zero, screen);
                if (hb != IntPtr.Zero) { SelectObject(mem, old); DeleteObject(hb); }
                DeleteDC(mem);
            }
        }

        [StructLayout(LayoutKind.Sequential)] struct POINT { public int x, y; }
        [StructLayout(LayoutKind.Sequential)] struct SIZE { public int cx, cy; }
        [StructLayout(LayoutKind.Sequential, Pack = 1)] struct BLENDFUNCTION { public byte BlendOp, BlendFlags, SourceConstantAlpha, AlphaFormat; }
        [DllImport("user32.dll")] static extern bool UpdateLayeredWindow(IntPtr hwnd, IntPtr hdcDst, ref POINT pptDst, ref SIZE psize, IntPtr hdcSrc, ref POINT pprSrc, int crKey, ref BLENDFUNCTION pblend, int dwFlags);
        [DllImport("user32.dll")] static extern IntPtr GetDC(IntPtr hWnd);
        [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);
        [DllImport("gdi32.dll")] static extern IntPtr CreateCompatibleDC(IntPtr hDC);
        [DllImport("gdi32.dll")] static extern bool DeleteDC(IntPtr hdc);
        [DllImport("gdi32.dll")] static extern IntPtr SelectObject(IntPtr hDC, IntPtr hObject);
        [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr hObject);
    }
}
