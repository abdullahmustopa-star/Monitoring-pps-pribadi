import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
import sqlite3
import shutil
import os

kivy.require('2.1.0')
Window.clearcolor = (0.93, 0.94, 0.96, 1)
DB_NAME = "monitoring_data.db"
DRIVE_DB_PATH = "/content/drive/MyDrive/APK_Monitoring/monitoring_data.db" 

def siapkan_database():
    if not os.path.exists(DB_NAME):
        if os.path.exists(DRIVE_DB_PATH):
            shutil.copy(DRIVE_DB_PATH, DB_NAME)
        else:
            print("⚠️ Database tidak ditemukan di Drive.")

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def hitung_ulang_semua():
    conn = get_db()
    cursor = conn.cursor()
    def get_a(n):
        cursor.execute("SELECT actual FROM indikator WHERE indikator=?", (n,))
        r = cursor.fetchone()
        return r[0] if r else 0
    def get_t(n):
        cursor.execute("SELECT target FROM indikator WHERE indikator=?", (n,))
        r = cursor.fetchone()
        return r[0] if r else 0
    def set_a(n, v):
        cursor.execute("UPDATE indikator SET actual=? WHERE indikator=?", (v, n))

    set_a('PWP Total (25%)', get_a('PWP 1') + get_a('PWP 2'))
    set_a('PSM Total (20%)', get_a('PSM 1') + get_a('PSM 2') + get_a('PSM 3') + get_a('PSM 4'))
    set_a('Serba Gratis Total (30%)', get_a('Serba Gratis 1') + get_a('Serba Gratis 2'))
    set_a('Net Sales Total', get_a('Net Sales Retail') + get_a('Net Sales E-Voucher'))

    apc_t, apc_a = get_t('APC vs Target (25%)'), get_a('APC vs Target (25%)')
    pwp_t, pwp_a = get_t('PWP Total (25%)'), get_a('PWP Total (25%)')
    psm_t, psm_a = get_t('PSM Total (20%)'), get_a('PSM Total (20%)')
    sg_t, sg_a = get_t('Serba Gratis Total (30%)'), get_a('Serba Gratis Total (30%)')

    penawaran = ((apc_a/apc_t*100 if apc_t else 0)*0.25) + ((pwp_a/pwp_t*100 if pwp_t else 0)*0.25) + \
                ((psm_a/psm_t*100 if psm_t else 0)*0.20) + ((sg_a/sg_t*100 if sg_t else 0)*0.30)
    set_a('Penawaran Langsung (%)', round(penawaran, 2))
    conn.commit()
    conn.close()

class MonitoringApp(App):
    def build(self):
        self.title = "Monitoring SAT"
        siapkan_database()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        header = Label(text="📊 Monitoring SAT", font_size='24sp', size_hint_y=None, height=60, bold=True, color=(0.1,0.2,0.5,1))
        layout.add_widget(header)
        
        scroll = ScrollView()
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.muat_data()
        scroll.add_widget(self.list_layout)
        layout.add_widget(scroll)
        
        btn_save = Button(text="💾 Simpan Perubahan", size_hint_y=None, height=60, background_color=(0.2, 0.7, 0.3, 1), bold=True)
        btn_save.bind(on_press=self.simpan_data)
        layout.add_widget(btn_save)
        return layout

    def muat_data(self):
        self.list_layout.clear_widgets()
        self.inputs = {}
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, indikator, target, actual, is_total FROM indikator ORDER BY id")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            box = BoxLayout(size_hint_y=None, height=65, spacing=5)
            nama_ind = row['indikator']
            is_lock = bool(row['is_total']) or ("Penawaran Langsung" in nama_ind)
            
            lbl = Label(text=nama_ind, size_hint_x=0.4, halign="left", valign="middle", bold=bool(row['is_total']), color=(0,0,0,1) if not row['is_total'] else (0.1,0.4,0.1,1))
            lbl.bind(size=lbl.setter('text_size'))
            box.add_widget(lbl)
            
            ti = TextInput(text=str(int(row['target'])), input_filter='float', size_hint_x=0.3, disabled=is_lock, halign='center', background_color=(0.9,0.9,0.9,1) if is_lock else (1,1,1,1))
            box.add_widget(ti)
            
            ai = TextInput(text=str(int(row['actual'])), input_filter='float', size_hint_x=0.3, disabled=is_lock, halign='center', background_color=(0.9,0.9,0.9,1) if is_lock else (1,1,1,1))
            box.add_widget(ai)
            
            self.inputs[row['id']] = {'target': ti, 'actual': ai, 'lock': is_lock}
            self.list_layout.add_widget(box)

    def simpan_data(self, instance):
        conn = get_db()
        cursor = conn.cursor()
        berhasil = 0
        for rid, fields in self.inputs.items():
            if not fields['lock']:
                try:
                    t_val = float(fields['target'].text or 0)
                    a_val = float(fields['actual'].text or 0)
                    cursor.execute("UPDATE indikator SET target=?, actual=? WHERE id=?", (t_val, a_val, rid))
                    berhasil += 1
                except ValueError:
                    pass
        conn.commit()
        conn.close()
        
        if berhasil > 0:
            hitung_ulang_semua()
            self.muat_data()
            popup = Popup(title='Sukses', content=Label(text='Data berhasil disimpan!'), size_hint=(0.8, 0.3))
            popup.open()

if __name__ == '__main__':
    MonitoringApp().run()
