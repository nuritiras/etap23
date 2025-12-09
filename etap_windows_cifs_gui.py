#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import textwrap

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class EtapWindowsCIFSGUI(Gtk.Window):
    def __init__(self):
        super().__init__(title="ETAP Haftalık Arka Plan (Windows CIFS) Kurulumu")
        self.set_border_width(10)
        self.set_default_size(700, 460)

        grid = Gtk.Grid(column_spacing=10, row_spacing=8)
        self.add(grid)

        row = 0

        # Sunucu IP
        grid.attach(Gtk.Label(label="Windows Server IP / Adı:", xalign=0), 0, row, 1, 1)
        self.entry_ip = Gtk.Entry()
        self.entry_ip.set_text("192.168.1.10")
        grid.attach(self.entry_ip, 1, row, 1, 1)
        row += 1

        # Paylaşım adı
        grid.attach(Gtk.Label(label="Paylaşım Adı (Share):", xalign=0), 0, row, 1, 1)
        self.entry_share = Gtk.Entry()
        self.entry_share.set_text("paylasim")
        grid.attach(self.entry_share, 1, row, 1, 1)
        row += 1

        # Alt klasör (arka plan klasörü)
        grid.attach(Gtk.Label(label="Alt Klasör (ör: arka-plan):", xalign=0), 0, row, 1, 1)
        self.entry_subdir = Gtk.Entry()
        self.entry_subdir.set_text("arka-plan")
        grid.attach(self.entry_subdir, 1, row, 1, 1)
        row += 1

        # Yerel mount noktası
        grid.attach(Gtk.Label(label="Yerel Mount Noktası:", xalign=0), 0, row, 1, 1)
        self.entry_mount = Gtk.Entry()
        self.entry_mount.set_text("/mnt/arka_plan")
        grid.attach(self.entry_mount, 1, row, 1, 1)
        row += 1

        # CIFS kullanıcı adı
        grid.attach(Gtk.Label(label="CIFS Kullanıcı Adı:", xalign=0), 0, row, 1, 1)
        self.entry_user = Gtk.Entry()
        self.entry_user.set_text("etapshare")
        grid.attach(self.entry_user, 1, row, 1, 1)
        row += 1

        # CIFS parola
        grid.attach(Gtk.Label(label="CIFS Parola:", xalign=0), 0, row, 1, 1)
        self.entry_pass = Gtk.Entry()
        self.entry_pass.set_visibility(False)  # şifre gizli
        grid.attach(self.entry_pass, 1, row, 1, 1)
        row += 1

        # SMB versiyon seçimi (isteğe bağlı, varsayılan 3.0)
        grid.attach(Gtk.Label(label="SMB Versiyonu (vers=):", xalign=0), 0, row, 1, 1)
        self.entry_smbvers = Gtk.Entry()
        self.entry_smbvers.set_text("3.0")
        grid.attach(self.entry_smbvers, 1, row, 1, 1)
        row += 1

        # Dconf kilidi
        self.chk_lock = Gtk.CheckButton(
            label="Kullanıcıların arka planı değiştirmesini engelle (dconf kilidi uygula)"
        )
        self.chk_lock.set_active(True)
        grid.attach(self.chk_lock, 0, row, 2, 1)
        row += 1

        # Açıklama
        info = Gtk.Label(
            label=(
                "Bu araç, Windows Server paylaşımlı haftalık arka plan sistemini kurar:\n"
                "- CIFS mount testi (Windows Server kullanıcı adı/parola ile)\n"
                "- systemd mount birimi (mnt-arka_plan.mount)\n"
                "- Haftalık arka plan betiği (/usr/local/bin/etap-haftalik-arka-plan.sh)\n"
                "- Tüm kullanıcılar için autostart kaydı (/etc/xdg/autostart/...)\n"
                "- İsteğe bağlı dconf kilidi (arka plan değişimini engeller)\n\n"
                "Lütfen root yetkisiyle çalıştırın:  sudo python3 etap_windows_cifs_gui.py"
            ),
            xalign=0
        )
        info.set_line_wrap(True)
        grid.attach(info, 0, row, 2, 1)
        row += 1

        # Kur / Uygula butonu
        self.btn_apply = Gtk.Button(label="Kur / Uygula")
        self.btn_apply.connect("clicked", self.on_apply_clicked)
        grid.attach(self.btn_apply, 0, row, 2, 1)
        row += 1

        # Çıktı alanı
        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.textview)
        grid.attach(scrolled, 0, row, 2, 1)

    def log(self, message: str):
        """Log alanına satır ekle ve aşağı kaydır."""
        buf = self.textview.get_buffer()
        end_iter = buf.get_end_iter()
        buf.insert(end_iter, message + "\n")
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self.textview.scroll_mark_onscreen(mark)
        while Gtk.events_pending():
            Gtk.main_iteration()

    def run_cmd(self, cmd, check=True):
        """Komut çalıştır, stdout/stderr'i logla."""
        self.log(f"$ {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=check
            )
            if result.stdout.strip():
                self.log(result.stdout.strip())
            if result.stderr.strip():
                self.log(result.stderr.strip())
            return result.returncode
        except subprocess.CalledProcessError as e:
            if e.stdout.strip():
                self.log(e.stdout.strip())
            if e.stderr.strip():
                self.log(f"HATA: {e.stderr.strip()}")
            if check:
                raise
            return e.returncode

    def test_cifs_path(self, what: str, username: str, password: str, vers: str) -> bool:
        """
        CIFS paylaşım yolunu geçici olarak test eder.
        Başarısız olursa gerçek hatayı log'a yazar ve False döner.
        """
        self.log(f"CIFS (Windows) yolu test ediliyor: {what}")
        test_dir = "/tmp/etap_arkaplan_cifs_test"
        os.makedirs(test_dir, exist_ok=True)

        # Eski mount'u varsa çöz
        subprocess.run(["umount", test_dir],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        options = f"username={username},password={password},vers={vers},iocharset=utf8,ro"
        cmd = ["mount", "-t", "cifs", what, test_dir, "-o", options]
        self.log(f"$ {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            self.log("CIFS testi BAŞARISIZ!")
            if result.stdout.strip():
                self.log(result.stdout.strip())
            if result.stderr.strip():
                self.log(result.stderr.strip())
            self.log("Lütfen IP / paylaşım / alt klasör / kullanıcı adı / parolanın doğru olduğundan emin olun.")
            return False

        # Başarılıysa tekrar umount et
        subprocess.run(["umount", test_dir],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        self.log("CIFS testi BAŞARILI. Windows Server'a erişilebiliyor.")
        return True

    def on_apply_clicked(self, button):
        # Log alanını temizle
        self.textview.get_buffer().set_text("")

        ip = self.entry_ip.get_text().strip()
        share = self.entry_share.get_text().strip()
        subdir = self.entry_subdir.get_text().strip().strip("/")
        mount_point = self.entry_mount.get_text().strip()
        username = self.entry_user.get_text().strip()
        password = self.entry_pass.get_text().strip()
        vers = self.entry_smbvers.get_text().strip() or "3.0"
        lock_enabled = self.chk_lock.get_active()

        if not ip or not share or not mount_point or not username or not password:
            self.log("Sunucu IP, paylaşım adı, mount noktası, kullanıcı adı ve parola boş olamaz.")
            return

        self.log(">>> Windows CIFS tabanlı haftalık arka plan kurulumu başlatılıyor...")

        # CIFS "What" değeri: //IP/Share/Subdir
        if subdir:
            what = f"//{ip}/{share}/{subdir}"
        else:
            what = f"//{ip}/{share}"

        try:
            # 0) CIFS yolu testi
            if not self.test_cifs_path(what, username, password, vers):
                self.log("HATA: CIFS bağlantı testi başarısız olduğu için kurulum durduruldu.")
                return

            # 1) Mount dizini
            self.log(f"Mount dizini oluşturuluyor: {mount_point}")
            os.makedirs(mount_point, exist_ok=True)

            # 2) systemd mount unit
            mount_unit_path = "/etc/systemd/system/mnt-arka_plan.mount"
            options_str = f"username={username},password={password},vers={vers},iocharset=utf8,ro"

            mount_unit_content = textwrap.dedent(f"""
                [Unit]
                Description=Windows Server Arka Plan Klasörü
                After=network-online.target

                [Mount]
                What={what}
                Where={mount_point}
                Type=cifs
                Options={options_str}

                [Install]
                WantedBy=multi-user.target
            """).strip() + "\n"

            self.log(f"{mount_unit_path} yazılıyor...")
            with open(mount_unit_path, "w", encoding="utf-8") as f:
                f.write(mount_unit_content)

            self.run_cmd(["systemctl", "daemon-reload"])
            rc = self.run_cmd(["systemctl", "enable", "--now", "mnt-arka_plan.mount"], check=False)
            if rc != 0:
                self.log("UYARI: mnt-arka_plan.mount başlatılırken hata oluştu. journalctl ile ayrıntı bakılabilir.")

            # 3) Haftalık arka plan betiği
            script_path = "/usr/local/bin/etap-haftalik-arka-plan.sh"
            script_content = textwrap.dedent(f"""
                #!/bin/bash

                # Haftanın numarasını al (01-52)
                WEEK_NUM=$(date +%V)

                # CIFS (Windows) klasöründeki resim
                REMOTE_IMG="{mount_point}/week${{WEEK_NUM}}.jpg"

                # Yerel arka plan dizini
                LOCAL_DIR="/home/$USER/.local/share/backgrounds"
                LOCAL_IMG="$LOCAL_DIR/week${{WEEK_NUM}}.jpg"

                mkdir -p "$LOCAL_DIR"

                if [ -f "$REMOTE_IMG" ]; then
                    cp "$REMOTE_IMG" "$LOCAL_IMG"
                    chown $USER:$USER "$LOCAL_IMG"

                    dconf write /org/cinnamon/desktop/background/picture-uri "'file://$LOCAL_IMG'"
                    dconf write /org/cinnamon/desktop/background/picture-options "'scaled'"
                else
                    echo "Bu haftaya ait arka plan bulunamadı: $REMOTE_IMG"
                fi
            """).strip() + "\n"

            self.log(f"{script_path} yazılıyor...")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)

            # 4) Tüm kullanıcılar için autostart kaydı
            autostart_path = "/etc/xdg/autostart/etap-haftalik-arka-plan.desktop"
            autostart_content = textwrap.dedent(f"""
                [Desktop Entry]
                Type=Application
                Name=ETAP Haftalık Arka Plan (Windows CIFS)
                Comment=Her oturum açılışında haftaya göre Windows Server arka planını uygular
                Exec={script_path}
                OnlyShowIn=X-Cinnamon;
                X-GNOME-Autostart-enabled=true
            """).strip() + "\n"

            self.log(f"{autostart_path} yazılıyor...")
            os.makedirs(os.path.dirname(autostart_path), exist_ok=True)
            with open(autostart_path, "w", encoding="utf-8") as f:
                f.write(autostart_content)

            # 5) Dconf kilidi (opsiyonel)
            if lock_enabled:
                self.log("Dconf kilitleme ayarları uygulanıyor...")
                os.makedirs("/etc/dconf/db/local.d", exist_ok=True)
                os.makedirs("/etc/dconf/db/local.d/locks", exist_ok=True)

                background_conf = "/etc/dconf/db/local.d/00-background"
                background_conf_content = textwrap.dedent("""
                    [org/cinnamon/desktop/background]
                    picture-options='scaled'
                """).strip() + "\n"
                with open(background_conf, "w", encoding="utf-8") as f:
                    f.write(background_conf_content)

                lock_file = "/etc/dconf/db/local.d/locks/background"
                lock_content = textwrap.dedent("""
                    /org/cinnamon/desktop/background/picture-uri
                    /org/cinnamon/desktop/background/picture-options
                """).strip() + "\n"
                with open(lock_file, "w", encoding="utf-8") as f:
                    f.write(lock_content)

                self.run_cmd(["dconf", "update"], check=False)

            self.log(">>> Kurulum tamamlandı. Herhangi bir kullanıcı ile oturum açıp test edebilirsiniz.")

        except Exception as e:
            self.log(f"GENEL HATA: {e}")


def main():
    win = EtapWindowsCIFSGUI()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

