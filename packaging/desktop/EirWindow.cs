using System;
using System.Diagnostics;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.WinForms;

static class EirWindow
{
    [STAThread]
    static void Main()
    {
        try
        {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        var form = new Form
        {
            Text = "EIR",
            Width = 1280,
            Height = 800,
            MinimumSize = new System.Drawing.Size(375, 640),
            StartPosition = FormStartPosition.CenterScreen,
            BackColor = System.Drawing.Color.FromArgb(11, 16, 32),
        };
        var exeIcon = System.Drawing.Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        if (exeIcon != null) form.Icon = exeIcon;
        var web = new WebView2 { Dock = DockStyle.Fill };
        form.Controls.Add(web);
        form.Shown += async (sender, args) =>
        {
            await web.EnsureCoreWebView2Async();
            web.CoreWebView2.NavigateToString(
                "<html><body style='background:#0b1020;color:#e8eefc;font-family:Segoe UI,sans-serif;padding:28px'><h1>EIR</h1><p>Demarrage de Docker, du bus MQTT et de MIMIR.</p></body></html>"
            );
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = "docker",
                    Arguments = "compose up -d",
                    WorkingDirectory = @"D:\PROBOOK 445 G7\Desktop\workshop\EIR",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
            }
            catch
            {
                // Docker can already be running.
            }
            if (await WaitReady())
            {
                web.CoreWebView2.Navigate("http://localhost:5173");
                return;
            }
            web.CoreWebView2.NavigateToString(
                "<html><body style='background:#0b1020;color:#e8eefc;font-family:Segoe UI,sans-serif;padding:28px'><h1>EIR</h1><p>Docker n'a pas ouvert l'interface. Verifie que Docker Desktop tourne, puis relance EIR.exe.</p></body></html>"
            );
        };
        Application.Run(form);
        }
        catch (Exception ex)
        {
            System.IO.File.WriteAllText(
                System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "EIR-error.txt"),
                ex.ToString());
        }
    }

    static async Task<bool> WaitReady()
    {
        using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(2) })
        {
        for (var i = 0; i < 90; i++)
        {
            try
            {
                var response = await http.GetAsync("http://localhost:5173");
                if (response.IsSuccessStatusCode) return true;
            }
            catch
            {
                // The site is still starting.
            }
            await Task.Delay(2000);
        }
        return false;
        }
    }
}
