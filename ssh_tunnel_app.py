#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading, socket, select, time, os

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

class SSHTunnelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SSH Tunnel Creator")
        self.root.geometry("650x550")
        self.ssh_client = None
        self.tunnel_active = False
        self.stop_tunnel = False
        self.create_widgets()

    def create_widgets(self):
        f = ttk.Frame(self.root, padding="10")
        f.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        r = 0
        ttk.Label(f, text="SSH Tunnel Creator", font=("Arial", 16, "bold")).grid(row=r, column=0, columnspan=2, pady=(0,20)); r+=1
        ttk.Label(f, text="SSH Server:").grid(row=r, column=0, sticky="w", pady=5)
        self.ssh_host = ttk.Entry(f, width=40); self.ssh_host.grid(row=r, column=1, sticky="we", pady=5); self.ssh_host.insert(0,"localhost"); r+=1
        ttk.Label(f, text="SSH Port:").grid(row=r, column=0, sticky="w", pady=5)
        self.ssh_port = ttk.Entry(f, width=10); self.ssh_port.grid(row=r, column=1, sticky="w", pady=5); self.ssh_port.insert(0,"22"); r+=1
        ttk.Label(f, text="Username:").grid(row=r, column=0, sticky="w", pady=5)
        self.username = ttk.Entry(f, width=40); self.username.grid(row=r, column=1, sticky="we", pady=5); r+=1
        ttk.Label(f, text="Password:").grid(row=r, column=0, sticky="w", pady=5)
        self.password = ttk.Entry(f, width=40, show="*"); self.password.grid(row=r, column=1, sticky="we", pady=5); r+=1
        ttk.Label(f, text="SSH Key (opt):").grid(row=r, column=0, sticky="w", pady=5)
        self.key_path = ttk.Entry(f, width=40); self.key_path.grid(row=r, column=1, sticky="we", pady=5)
        ttk.Button(f, text="Browse...", command=self.browse_key).grid(row=r, column=2, padx=5); r+=1
        ttk.Separator(f).grid(row=r, column=0, columnspan=3, sticky="we", pady=15); r+=1
        ttk.Label(f, text="Local Forward:", font=("Arial", 10, "bold")).grid(row=r, column=0, sticky="w", pady=5); r+=1
        self.local_bind = ttk.Entry(f, width=15); self.local_bind.grid(row=r, column=1, sticky="w", pady=5); self.local_bind.insert(0,"8080")
        ttk.Label(f, text="->").grid(row=r, column=2, padx=5)
        self.local_dest = ttk.Entry(f, width=25); self.local_dest.grid(row=r, column=3, sticky="w", pady=5); self.local_dest.insert(0,"remote-host:80"); r+=1
        ttk.Label(f, text="Dynamic (SOCKS):").grid(row=r, column=0, sticky="w", pady=5)
        self.dynamic_port = ttk.Entry(f, width=15); self.dynamic_port.grid(row=r, column=1, sticky="w", pady=5); r+=1
        ttk.Separator(f).grid(row=r, column=0, columnspan=4, sticky="we", pady=15); r+=1
        bf = ttk.Frame(f); bf.grid(row=r, column=0, columnspan=4, pady=10)
        self.btn_conn = ttk.Button(bf, text="Connect", command=self.start_tunnel); self.btn_conn.pack(side="left", padx=5)
        self.btn_disc = ttk.Button(bf, text="Disconnect", command=self.stop_action, state="disabled"); self.btn_disc.pack(side="left", padx=5); r+=1
        sf = ttk.LabelFrame(f, text="Status", padding="5"); sf.grid(row=r, column=0, columnspan=4, sticky="we", pady=10)
        self.status_lbl = ttk.Label(sf, text="Not connected", foreground="red"); self.status_lbl.grid(row=0, column=0, sticky="w"); r+=1
        lf = ttk.LabelFrame(f, text="Log", padding="5"); lf.grid(row=r, column=0, columnspan=4, sticky="nsew", pady=10)
        lf.columnconfigure(0, weight=1); lf.rowconfigure(0, weight=1)
        self.log_txt = scrolledtext.ScrolledText(lf, height=10, width=70); self.log_txt.grid(row=0, column=0, sticky="nsew")
        f.rowconfigure(r, weight=1)
        self.log("Application started")

    def browse_key(self):
        from tkinter import filedialog
        fn = filedialog.askopenfilename(title="SSH key", filetypes=[("Keys","*.pem *.ppk *"),("All","*.*")])
        if fn: self.key_path.delete(0,"end"); self.key_path.insert(0,fn)

    def log(self, msg):
        self.log_txt.insert("end", "[{}] {}\n".format(time.strftime('%H:%M:%S'), msg)); self.log_txt.see("end")

    def get_int(self, t, d):
        try: return int(t.strip())
        except: return d

    def parse_cfg(self, b, d):
        try:
            bp = self.get_int(b, 0)
            if not bp: return None
            if ':' in d:
                p = d.rsplit(':',1); dh = p[0].strip(); dp = self.get_int(p[1], 0)
            else: dh = 'localhost'; dp = self.get_int(d, 0)
            if dp: return (bp, dh, dp)
        except: pass
        return None

    def start_tunnel(self):
        if not PARAMIKO_AVAILABLE:
            messagebox.showerror("Error", "Install: pip install paramiko"); return
        h = self.ssh_host.get().strip(); p = self.get_int(self.ssh_port.get(), 22)
        u = self.username.get().strip(); pw = self.password.get(); kp = self.key_path.get().strip()
        if not h: messagebox.showwarning("Warning", "Enter SSH server"); return
        if not u and not kp: messagebox.showwarning("Warning", "Enter username or key"); return
        lc = self.parse_cfg(self.local_bind.get(), self.local_dest.get())
        dp = self.get_int(self.dynamic_port.get(), 0)
        if not lc and not dp: messagebox.showwarning("Warning", "Configure tunnel"); return
        self.btn_conn.config(state="disabled")
        threading.Thread(target=self._connect, args=(h,p,u,pw,kp,lc,dp), daemon=True).start()

    def _connect(self, h, p, u, pw, kp, lc, dp):
        try:
            self.log("Connecting to {}:{}...".format(h,p))
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if kp and os.path.exists(kp):
                key = None
                for kc in [paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey, paramiko.Ed25519Key]:
                    try: key = kc.from_private_key_file(kp); break
                    except: continue
                if not key: raise Exception("Failed to load key")
                self.ssh_client.connect(hostname=h, port=p, username=u, pkey=key, timeout=10)
            else:
                self.ssh_client.connect(hostname=h, port=p, username=u, password=pw, timeout=10)
            self.log("SSH connected!")
            self.tunnel_active = True
            self.root.after(0, lambda: self.update_status(True))
            tunnels = []
            if lc:
                bp, dh, dp2 = lc
                tr = self.ssh_client.get_transport()
                tr.request_port_forward('', bp)
                threading.Thread(target=self._local_fwd, args=(bp,dh,dp2), daemon=True).start()
                tunnels.append("Local: {}->{}:{}".format(bp,dh,dp2))
                self.log("Local tunnel: {}->{}:{}".format(bp,dh,dp2))
            if dp:
                threading.Thread(target=self._dyn_fwd, args=(dp,), daemon=True).start()
                tunnels.append("SOCKS: {}".format(dp))
                self.log("SOCKS proxy on port {}".format(dp))
            self.log("Tunnels: {}".format(', '.join(tunnels)))
            while self.tunnel_active and not self.stop_tunnel: time.sleep(0.5)
        except Exception as e:
            self.log("Error: {}".format(e))
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.update_status(False))
        finally: self.cleanup()

    def _local_fwd(self, bp, dh, dp):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(('127.0.0.1', bp)); srv.listen(5); srv.settimeout(1.0)
            while self.tunnel_active and not self.stop_tunnel:
                try:
                    c, a = srv.accept()
                    threading.Thread(target=self._fwd, args=(c,dh,dp), daemon=True).start()
                except socket.timeout: continue
                except: break
            srv.close()
        except Exception as e: self.log("Local fwd error: {}".format(e))

    def _fwd(self, c, dh, dp):
        try:
            r = socket.create_connection((dh, dp), timeout=5); r.settimeout(1.0)
            skts = [c, r]
            while self.tunnel_active and not self.stop_tunnel:
                try:
                    rd, _, _ = select.select(skts, [], [], 1.0)
                    for s in rd:
                        o = r if s is c else c; d = s.recv(4096)
                        if not d: return
                        o.sendall(d)
                except: break
        except: pass
        finally:
            try: c.close()
            except: pass

    def _dyn_fwd(self, bp):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(('127.0.0.1', bp)); srv.listen(5); srv.settimeout(1.0)
            self.log("SOCKS started on 127.0.0.1:{}".format(bp))
            while self.tunnel_active and not self.stop_tunnel:
                try:
                    c, a = srv.accept()
                    threading.Thread(target=self._socks, args=(c,), daemon=True).start()
                except socket.timeout: continue
                except: break
            srv.close()
        except Exception as e: self.log("SOCKS error: {}".format(e))

    def _socks(self, c):
        try:
            c.settimeout(5.0)
            v = c.recv(1)
            if v != b'\x05': c.close(); return
            nm = ord(c.recv(1)); c.recv(nm); c.send(b'\x05\x00')
            c.recv(1); c.recv(1); c.recv(1); at = ord(c.recv(1))
            if at == 1: da = c.recv(4); di = '.'.join(str(ord(b)) for b in da)
            elif at == 3: ln = ord(c.recv(1)); da = c.recv(ln); di = da.decode()
            elif at == 4: da = c.recv(16); di = ':'.join(format(ord(b),'02x') for b in da)
            else: c.close(); return
            dpt = ord(c.recv(1))*256 + ord(c.recv(1))
            self.log("SOCKS: {}:{}".format(di,dpt))
            c.send(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
            tr = self.ssh_client.get_transport()
            ch = tr.open_channel('direct-tcpip', (di, dpt), ('127.0.0.1', 0))
            skts = [c, ch]
            while self.tunnel_active and not self.stop_tunnel:
                try:
                    rd, _, _ = select.select(skts, [], [], 1.0)
                    for s in rd:
                        o = ch if s is c else c; d = s.recv(4096)
                        if not d: return
                        o.sendall(d)
                except: break
        except Exception as e: self.log("SOCKS err: {}".format(e))
        finally:
            try: c.close()
            except: pass

    def stop_action(self):
        self.log("Stopping..."); self.stop_tunnel = True; self.tunnel_active = False

    def cleanup(self):
        if self.ssh_client:
            try: self.ssh_client.close()
            except: pass
            self.ssh_client = None
        self.root.after(0, lambda: self.update_status(False))
        self.root.after(0, lambda: self.btn_conn.config(state="normal"))
        self.root.after(0, lambda: self.btn_disc.config(state="disabled"))
        self.stop_tunnel = False; self.tunnel_active = False

    def update_status(self, ok):
        if ok: self.status_lbl.config(text="Connected", foreground="green"); self.btn_disc.config(state="normal")
        else: self.status_lbl.config(text="Not connected", foreground="red"); self.btn_disc.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    SSHTunnelApp(root)
    root.mainloop()
