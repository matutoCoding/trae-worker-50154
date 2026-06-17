import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta, date
from db.database import init_db, create_sample_data
from models.user import User, UserRole
from models.booking import BookingStatus
from services.user_service import UserService
from services.cage_service import CageService
from services.booking_service import BookingService
from services.conflict_service import ConflictService
from services.approval_service import ApprovalService
from services.access_service import AccessService

class AnimalLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("实验动物房预约管理系统")
        self.geometry("1200x700)
        self.current_user = None
        
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        
        init_db()
        create_sample_data()
        
        self._show_login()

    def _show_login(self):
        for widget in self.winfo_children():
            widget.destroy()
        
        login_frame = ttk.Frame(self, padding=40)
        login_frame.pack(expand=True)
        
        ttk.Label(login_frame, text="🔬 实验动物房预约管理系统", 
                   font=('微软雅黑', 20, 'bold')).pack(pady=(0, 10))
        ttk.Label(login_frame, text="请登录以继续", font=('微软雅黑', 10)).pack(pady=(0, 30))
        
        ttk.Label(login_frame, text="用户名：", font=('微软雅黑', 10)).pack(anchor='w')
        self.username_entry = ttk.Entry(login_frame, font=('微软雅黑', 12))
        self.username_entry.pack(fill='x', pady=(0, 15))
        self.username_entry.insert(0, 'student1')
        self.username_entry.focus()
        
        ttk.Label(login_frame, text="密  码：", font=('微软雅黑', 10)).pack(anchor='w')
        self.password_entry = ttk.Entry(login_frame, show='*', font=('微软雅黑', 12))
        self.password_entry.pack(fill='x', pady=(0, 20))
        self.password_entry.insert(0, '123456')
        
        ttk.Label(login_frame, text="测试账号：student1 / advisor1 / manager1 / ethics1，密码均为 123456",
                   font=('微软雅黑', 8), foreground='gray').pack(pady=(0, 20))
        
        login_btn = tk.Button(login_frame, text="登 录", font=('微软雅黑', 12, 'bold'),
                             bg='#3498db', fg='white', width=15, command=self._on_login)
        login_btn.pack(pady=10)
        
        self.bind('<Return>', lambda e: self._on_login())

    def _on_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        success, user, msg = UserService.authenticate(username, password)
        if success:
            self.current_user = user
            self._build_main_ui()
        else:
            messagebox.showerror("登录失败", msg)

    def _build_main_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
        
        header = tk.Frame(self, bg='#2c3e50', height=60)
        header.pack(fill='x')
        
        tk.Label(header, text="🐭 实验动物房预约管理系统", 
                  bg='#2c3e50', fg='white', 
                  font=('微软雅黑', 14, 'bold')).pack(side='left', padx=20, pady=15)
        
        role_name = UserService.get_role_name(self.current_user.role)
        tk.Label(header, text=f"👤 {self.current_user.name} ({role_name})",
                bg='#2c3e50', fg='white', font=('微软雅黑', 10)).pack(side='right', padx=10, pady=15)
        
        logout_btn = tk.Button(header, text="退出", bg='#e74c3c', fg='white',
                              relief='flat', padx=15, command=self._logout)
        logout_btn.pack(side='right', padx=10, pady=10)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.cage_tab = tk.Frame(self.notebook)
        self.booking_tab = tk.Frame(self.notebook)
        self.approval_tab = tk.Frame(self.notebook)
        self.access_tab = tk.Frame(self.notebook)
        
        self.notebook.add(self.cage_tab, text='🏠 笼位排期')
        self.notebook.add(self.booking_tab, text='📋 我的预约')
        self.notebook.add(self.approval_tab, text='✅ 审批管理')
        self.notebook.add(self.access_tab, text='🔐 准入登记')
        
        self._build_cage_tab()
        self._build_booking_tab()
        self._build_approval_tab()
        self._build_access_tab()
        
        self._refresh_cage_tab()
        self._refresh_booking_tab()
        self._refresh_approval_tab()
        self._refresh_access_tab()

    def _logout(self):
        if messagebox.askyesno("确认", "确定要退出登录吗？"):
            self.current_user = None
            self._show_login()

    def _build_cage_tab(self):
        frame = self.cage_tab
        for widget in frame.winfo_children():
            widget.destroy()
        
        main_paned = tk.PanedWindow(frame, orient='horizontal')
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        left_frame = tk.Frame(main_paned, width=250)
        main_paned.add(left_frame)
        
        tk.Label(left_frame, text="笼位列表", font=('微软雅黑', 11, 'bold')).pack(pady=5)
        
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill='x', pady=5)
        tk.Button(btn_frame, text="🔄 刷新", width=8, command=self._refresh_cage_tab).pack(side='left', padx=2)
        if self.current_user.role == UserRole.FACILITY_MANAGER:
            tk.Button(btn_frame, text="➕ 新增", width=8, bg='#409eff', fg='white',
                     command=self._add_cage).pack(side='left', padx=2)
        
        self.cage_listbox = tk.Listbox(left_frame, font=('微软雅黑', 10))
        self.cage_listbox.pack(fill='both', expand=True, padx=5)
        self.cage_listbox.bind('<<ListboxSelect>>', self._on_cage_select)
        
        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame)
        
        ctrl_frame = tk.Frame(right_frame)
        ctrl_frame.pack(fill='x', pady=5)
        
        tk.Label(ctrl_frame, text="日期：").pack(side='left', padx=5)
        self.cage_date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        self.cage_date_entry = tk.Entry(ctrl_frame, textvariable=self.cage_date_var, width=12)
        self.cage_date_entry.pack(side='left')
        tk.Button(ctrl_frame, text="◀", width=3, command=self._prev_day).pack(side='left', padx=2)
        tk.Button(ctrl_frame, text="▶", width=3, command=self._next_day).pack(side='left', padx=2)
        tk.Button(ctrl_frame, text="今天", width=6, command=self._today).pack(side='left', padx=2)
        
        if self.current_user.role == UserRole.RESEARCHER:
            tk.Button(ctrl_frame, text="📅 新建预约", bg='#67c23a', fg='white',
                     command=self._create_booking).pack(side='right', padx=5)
        
        tk.Label(right_frame, text="时段排期表", font=('微软雅黑', 11, 'bold')).pack(anchor='w', padx=5, pady=(10, 5))
        
        columns = ('time', 'info', 'status')
        self.cage_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=20)
        self.cage_tree.heading('time', text='时段')
        self.cage_tree.heading('info', text='预约信息')
        self.cage_tree.heading('status', text='状态')
        self.cage_tree.column('time', width=120)
        self.cage_tree.column('info', width=400)
        self.cage_tree.column('status', width=100)
        
        self.cage_tree.tag_configure('available', background='#f0f9eb')
        self.cage_tree.tag_configure('pending', background='#fdf6ec')
        self.cage_tree.tag_configure('approved', background='#fef0f0')
        
        self.cage_tree.pack(fill='both', expand=True, padx=5)
        
        self.selected_cage = None

    def _refresh_cage_tab(self):
        self.cage_listbox.delete(0, tk.END)
        cages = CageService.get_all_cages()
        self.cages = cages
        for cage in cages:
            status_icon = {'available': '🟢', 'occupied': '🔴', 'maintenance': '🟡'}.get(cage.status.value, '⚪')
            self.cage_listbox.insert(tk.END, f"{status_icon} [{cage.cage_code}] {cage.room} - {cage.animal_type}")
        
        self._refresh_schedule()

    def _on_cage_select(self, event):
        selection = self.cage_listbox.curselection()
        if selection:
            self.selected_cage = self.cages[selection[0]]
            self._refresh_schedule()

    def _prev_day(self):
        try:
            d = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
            self.cage_date_var.set((d - timedelta(days=1)).strftime('%Y-%m-%d'))
            self._refresh_schedule()
        except: pass

    def _next_day(self):
        try:
            d = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
            self.cage_date_var.set((d + timedelta(days=1)).strftime('%Y-%m-%d'))
            self._refresh_schedule()
        except: pass

    def _today(self):
        self.cage_date_var.set(date.today().strftime('%Y-%m-%d'))
        self._refresh_schedule()

    def _refresh_schedule(self):
        for item in self.cage_tree.get_children():
            self.cage_tree.delete(item)
        
        if not self.selected_cage:
            return
            
        try:
            sel_date = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
        except:
            sel_date = date.today()
            
        start_dt = datetime.combine(sel_date, datetime.min.time())
        end_dt = datetime.combine(sel_date + timedelta(days=1), datetime.min.time())
        
        bookings = ConflictService.get_cage_bookings_in_range(
            self.selected_cage.id, start_dt, end_dt
        )
        
        for hour in range(8, 20):
            slot_start = datetime.combine(sel_date, time(hour, 0))
            slot_end = datetime.combine(sel_date, time(hour + 1, 0))
            
            time_str = f"{slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}"
            
            info = ''
            status = '空闲'
            tag = 'available'
            
            for booking in bookings:
                if ConflictService.check_time_overlap(slot_start, slot_end, 
                                                      booking.start_time, booking.end_time):
                    if booking.status not in [BookingStatus.REJECTED, BookingStatus.CANCELLED]:
                        info = (f"#{booking.id} {booking.project_name} - {booking.researcher.name}\n"
                               f"  {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}")
                        status = BookingService.get_booking_status_text(booking.status)
                        tag = 'pending' if '待' in status else 'approved'
                        break
            
            if not info:
                info = '可预约'
            
            self.cage_tree.insert('', tk.END, values=(time_str, info, status), tags=(tag,))

    def _add_cage(self):
        dialog = tk.Toplevel(self)
        dialog.title("新增笼位")
        dialog.geometry("400x350")
        
        form = tk.Frame(dialog, padding=20)
        form.pack(fill='both', expand=True)
        
        entries = {}
        fields = [('笼位编号', 'cage_code'), ('所在房间', 'room'), 
                  ('容纳数量', 'capacity'), ('动物类型', 'animal_type')]
        
        for i, (label, key) in enumerate(fields):
            tk.Label(form, text=f"{label}：", font=('微软雅黑', 10)).grid(row=i, column=0, sticky='e', pady=8)
            if key == 'capacity':
                entry = tk.Spinbox(form, from_=1, to=100, width=23)
            else:
                entry = tk.Entry(form, width=25)
            entry.grid(row=i, column=1, pady=8)
            entries[key] = entry
        
        tk.Label(form, text="备注：", font=('微软雅黑', 10)).grid(row=4, column=0, sticky='ne', pady=8)
        desc_text = tk.Text(form, width=25, height=4)
        desc_text.grid(row=4, column=1, pady=8)
        
        def save():
            data = {k: (v.get() if not isinstance(v, tk.Text) else v.get('1.0', tk.END).strip())
                   for k, v in entries.items()}
            data['capacity'] = int(data['capacity'])
            data['description'] = desc_text.get('1.0', tk.END).strip()
            
            if not all([data['cage_code'], data['room'], data['animal_type']]):
                messagebox.showwarning("提示", "请填写完整信息")
                return
                
            success, msg, _ = CageService.create_cage(**data)
            if success:
                messagebox.showinfo("成功", msg)
                dialog.destroy()
                self._refresh_cage_tab()
            else:
                messagebox.showerror("失败", msg)
        
        btn_frame = tk.Frame(form)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        tk.Button(btn_frame, text="确定", width=10, bg='#67c23a', fg='white', command=save).pack(side='left', padx=10)
        tk.Button(btn_frame, text="取消", width=10, command=dialog.destroy).pack(side='right', padx=10)

    def _create_booking(self):
        if not self.selected_cage:
            messagebox.showwarning("提示", "请先选择一个笼位")
            return
            
        dialog = tk.Toplevel(self)
        dialog.title("新建预约")
        dialog.geometry("450x450")
        
        form = tk.Frame(dialog, padding=20)
        form.pack(fill='both', expand=True)
        
        tk.Label(form, text=f"笼位：{self.selected_cage.cage_code} ({self.selected_cage.room} - {self.selected_cage.animal_type})",
                 font=('微软雅黑', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=10, sticky='w')
        tk.Label(form, text=f"申请人：{self.current_user.name}", font=('微软雅黑', 10, 'bold')).grid(row=1, column=0, columnspan=2, pady=5, sticky='w')
        
        tk.Label(form, text="项目名称：").grid(row=2, column=0, sticky='e', pady=8)
        project_entry = tk.Entry(form, width=30)
        project_entry.grid(row=2, column=1, pady=8)
        
        tk.Label(form, text=f"动物数量(1-{self.selected_cage.capacity})：").grid(row=3, column=0, sticky='e', pady=8)
        count_spin = tk.Spinbox(form, from_=1, to=self.selected_cage.capacity, width=28)
        count_spin.grid(row=3, column=1, pady=8)
        
        try:
            sel_date = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
        except:
            sel_date = date.today()
            
        tk.Label(form, text="预约日期：").grid(row=4, column=0, sticky='e', pady=8)
        date_entry = tk.Entry(form, width=30)
        date_entry.insert(0, sel_date.strftime('%Y-%m-%d'))
        date_entry.grid(row=4, column=1, pady=8)
        
        tk.Label(form, text="开始时间：").grid(row=5, column=0, sticky='e', pady=8)
        start_entry = tk.Entry(form, width=30)
        start_entry.insert(0, "09:00")
        start_entry.grid(row=5, column=1, pady=8)
        
        tk.Label(form, text="结束时间：").grid(row=6, column=0, sticky='e', pady=8)
        end_entry = tk.Entry(form, width=30)
        end_entry.insert(0, "12:00")
        end_entry.grid(row=6, column=1, pady=8)
        
        tk.Label(form, text="实验目的：").grid(row=7, column=0, sticky='ne', pady=8)
        purpose_text = tk.Text(form, width=30, height=5)
        purpose_text.grid(row=7, column=1, pady=8)
        
        result_label = tk.Label(form, text="", font=('微软雅黑', 9))
        result_label.grid(row=8, column=0, columnspan=2, pady=5)
        
        def check_conflict():
            try:
                d = datetime.strptime(date_entry.get(), '%Y-%m-%d').date()
                sh, sm = map(int, start_entry.get().split(':'))
                eh, em = map(int, end_entry.get().split(':'))
                start_dt = datetime.combine(d, time(sh, sm))
                end_dt = datetime.combine(d, time(eh, em))
                
                is_valid, _, msg = ConflictService.validate_booking(self.selected_cage.id, start_dt, end_dt)
                if is_valid:
                    result_label.config(text=f"✓ {msg}", fg='green')
                else:
                    result_label.config(text=f"✗ {msg}", fg='red')
            except Exception as e:
                result_label.config(text=f"✗ 时间格式错误", fg='red')
        
        tk.Button(form, text="🔍 检测冲突", command=check_conflict).grid(row=9, column=0, columnspan=2, pady=5)
        
        def save():
            try:
                project = project_entry.get().strip()
                count = int(count_spin.get())
                purpose = purpose_text.get('1.0', tk.END).strip()
                
                d = datetime.strptime(date_entry.get(), '%Y-%m-%d').date()
                sh, sm = map(int, start_entry.get().split(':'))
                eh, em = map(int, end_entry.get().split(':'))
                start_dt = datetime.combine(d, time(sh, sm))
                end_dt = datetime.combine(d, time(eh, em))
                
                if not all([project, purpose]):
                    messagebox.showwarning("提示", "请填写完整信息")
                    return
                    
                success, msg, booking = BookingService.create_booking(
                    cage_id=self.selected_cage.id,
                    researcher_id=self.current_user.id,
                    project_name=project,
                    animal_count=count,
                    start_time=start_dt,
                    end_time=end_dt,
                    purpose=purpose
                )
                
                if success:
                    messagebox.showinfo("成功", f"{msg}\n\n预约编号：#{booking.id}\n当前状态：草稿\n\n可在'我的预约'中提交审批")
                    dialog.destroy()
                    self._refresh_schedule()
                    self._refresh_booking_tab()
                else:
                    messagebox.showerror("失败", msg)
            except Exception as e:
                messagebox.showerror("错误", f"输入格式错误：{str(e)}")
        
        btn_frame = tk.Frame(form)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=15)
        tk.Button(btn_frame, text="确定", width=10, bg='#67c23a', fg='white', command=save).pack(side='left', padx=10)
        tk.Button(btn_frame, text="取消", width=10, command=dialog.destroy).pack(side='right', padx=10)

    def _build_booking_tab(self):
        frame = self.booking_tab
        for widget in frame.winfo_children():
            widget.destroy()
        
        top_frame = tk.Frame(frame)
        top_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(top_frame, text="状态筛选：").pack(side='left', padx=5)
        self.booking_filter_var = tk.StringVar(value="全部")
        filter_combo = ttk.Combobox(top_frame, textvariable=self.booking_filter_var, width=15, state='readonly')
        filter_combo['values'] = ['全部'] + [BookingService.get_booking_status_text(s) for s in BookingStatus]
        filter_combo.pack(side='left')
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_booking_tab())
        
        tk.Button(top_frame, text="🔄 刷新", command=self._refresh_booking_tab).pack(side='right', padx=5)
        
        columns = ('id', 'project', 'cage', 'time', 'count', 'status', 'reason')
        self.booking_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.booking_tree.heading('id', text='ID')
        self.booking_tree.heading('project', text='项目名称')
        self.booking_tree.heading('cage', text='笼位')
        self.booking_tree.heading('time', text='时段')
        self.booking_tree.heading('count', text='数量')
        self.booking_tree.heading('status', text='状态')
        self.booking_tree.heading('reason', text='驳回原因')
        self.booking_tree.column('id', width=50)
        self.booking_tree.column('project', width=200)
        self.booking_tree.column('cage', width=120)
        self.booking_tree.column('time', width=250)
        self.booking_tree.column('count', width=60)
        self.booking_tree.column('status', width=100)
        self.booking_tree.column('reason', width=150)
        self.booking_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        detail_frame = tk.LabelFrame(frame, text="预约详情", padding=10)
        detail_frame.pack(fill='x', padx=5, pady=5)
        
        self.booking_detail = tk.Text(detail_frame, height=5, font=('微软雅黑', 9))
        self.booking_detail.pack(fill='x')
        self.booking_detail.config(state='disabled')
        
        btn_frame = tk.Frame(detail_frame)
        btn_frame.pack(fill='x', pady=5)
        
        self.submit_btn = tk.Button(btn_frame, text="📤 提交审批", bg='#409eff', fg='white', state='disabled', command=self._submit_booking)
        self.submit_btn.pack(side='left', padx=5)
        self.cancel_btn = tk.Button(btn_frame, text="❌ 取消预约", bg='#f56c6c', fg='white', state='disabled', command=self._cancel_booking)
        self.cancel_btn.pack(side='left', padx=5)
        self.history_btn = tk.Button(btn_frame, text="📜 审批记录", state='disabled', command=self._view_approval_history)
        self.history_btn.pack(side='left', padx=5)
        
        self.booking_tree.bind('<<TreeviewSelect>>', self._on_booking_select)

    def _refresh_booking_tab(self):
        for item in self.booking_tree.get_children():
            self.booking_tree.delete(item)
        
        if self.current_user.role == UserRole.RESEARCHER:
            bookings = BookingService.get_bookings_by_researcher(self.current_user.id)
        else:
            bookings = BookingService.get_all_bookings()
        
        filter_text = self.booking_filter_var.get()
        if filter_text != '全部':
            bookings = [b for b in bookings if BookingService.get_booking_status_text(b.status) == filter_text]
        
        for booking in bookings:
            time_str = (f"{booking.start_time.strftime('%Y-%m-%d %H:%M')}\n"
                      f"{booking.end_time.strftime('%Y-%m-%d %H:%M')}")
            status = BookingService.get_booking_status_text(booking.status)
            self.booking_tree.insert('', tk.END, 
                values=(booking.id, booking.project_name, 
                       f"{booking.cage.cage_code} ({booking.cage.room})",
                       time_str, booking.animal_count, status, booking.reject_reason or '-'),
                tags=(booking.status.value,))

    def _on_booking_select(self, event):
        selection = self.booking_tree.selection()
        if not selection:
            self.booking_detail.config(state='normal')
            self.booking_detail.delete('1.0', tk.END)
            self.booking_detail.config(state='disabled')
            self.submit_btn.config(state='disabled')
            self.cancel_btn.config(state='disabled')
            self.history_btn.config(state='disabled')
            return
            
        item = self.booking_tree.item(selection[0])
        booking_id = item['values'][0]
        booking = BookingService.get_booking_by_id(booking_id)
        
        detail = (f"预约编号：#{booking.id}\n"
                 f"项目名称：{booking.project_name}\n"
                 f"笼位：{booking.cage.cage_code} - {booking.cage.room}\n"
                 f"动物：{booking.cage.animal_type} × {booking.animal_count}\n"
                 f"时段：{booking.start_time.strftime('%Y-%m-%d %H:%M')} 至 {booking.end_time.strftime('%Y-%m-%d %H:%M')}\n"
                 f"申请人：{booking.researcher.name}\n"
                 f"状态：{BookingService.get_booking_status_text(booking.status)}\n"
                 f"实验目的：{booking.purpose}")
        if booking.reject_reason:
            detail += f"\n驳回原因：{booking.reject_reason}"
        
        self.booking_detail.config(state='normal')
        self.booking_detail.delete('1.0', tk.END)
        self.booking_detail.insert('1.0', detail)
        self.booking_detail.config(state='disabled')
        
        is_researcher = self.current_user.role == UserRole.RESEARCHER
        is_own = booking.researcher_id == self.current_user.id
        
        self.submit_btn.config(state='normal' if (is_researcher and is_own and booking.status == BookingStatus.DRAFT) else 'disabled')
        self.cancel_btn.config(state='normal' if (is_researcher and is_own and booking.status not in 
                              [BookingStatus.CANCELLED, BookingStatus.REJECTED, BookingStatus.COMPLETED]) else 'disabled')
        self.history_btn.config(state='normal' if len(booking.approvals) > 0 else 'disabled')

    def _submit_booking(self):
        selection = self.booking_tree.selection()
        if not selection:
            return
            
        item = self.booking_tree.item(selection[0])
        booking_id = item['values'][0]
        
        if messagebox.askyesno("确认", f"确定要提交预约 #{booking_id} 进入审批流程吗？\n\n审批流程：导师 → 动物房管理员 → 伦理委员会"):
            success, msg = BookingService.submit_booking(booking_id)
            if success:
                messagebox.showinfo("成功", msg)
                self._refresh_booking_tab()
            else:
                messagebox.showerror("失败", msg)

    def _cancel_booking(self):
        selection = self.booking_tree.selection()
        if not selection:
            return
            
        item = self.booking_tree.item(selection[0])
        booking_id = item['values'][0]
        
        if messagebox.askyesno("确认", f"确定要取消预约 #{booking_id} 吗？\n\n取消后时段将被释放。"):
            success, msg = BookingService.cancel_booking(booking_id)
            if success:
                messagebox.showinfo("成功", msg)
                self._refresh_booking_tab()
                self._refresh_cage_tab()
            else:
                messagebox.showerror("失败", msg)

    def _view_approval_history(self):
        selection = self.booking_tree.selection()
        if not selection:
            return
            
        item = self.booking_tree.item(selection[0])
        booking_id = item['values'][0]
        
        approvals = ApprovalService.get_approval_history(booking_id)
        
        dialog = tk.Toplevel(self)
        dialog.title("审批记录")
        dialog.geometry("500x400")
        
        text = tk.Text(dialog, font=('微软雅黑', 10), padding=15)
        text.pack(fill='both', expand=True)
        
        node_names = {'advisor': '导师审批', 'facility_manager': '管理员审批', 'ethics_committee': '伦理审批'}
        status_names = {'pending': '待处理', 'approved': '✓ 通过', 'rejected': '✗ 驳回'}
        
        for i, approval in enumerate(approvals, 1):
            node_name = node_names.get(approval.node.value, approval.node.value)
            status = status_names.get(approval.status.value, approval.status.value)
            color = 'green' if approval.status.value == 'approved' else 'red' if approval.status.value == 'rejected' else 'orange'
            
            text.insert(tk.END, f"【第 {i} 步】{node_name}\n")
            text.insert(tk.END, f"结果：{status}\n", color)
            text.insert(tk.END, f"审批人：{approval.approver.name}\n")
            text.insert(tk.END, f"时间：{approval.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            text.insert(tk.END, f"意见：{approval.comments or '无'}\n\n")
        
        text.tag_config('green', foreground='green')
        text.tag_config('red', foreground='red')
        text.tag_config('orange', foreground='orange')
        text.config(state='disabled')
        
        tk.Button(dialog, text="关闭", width=10, command=dialog.destroy).pack(pady=10)

    def _build_approval_tab(self):
        frame = self.approval_tab
        for widget in frame.winfo_children():
            widget.destroy()
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        pending_frame = tk.Frame(notebook)
        notebook.add(pending_frame, text='⏳ 待我审批')
        
        history_frame = tk.Frame(notebook)
        notebook.add(history_frame, text='📜 审批历史')
        
        top1 = tk.Frame(pending_frame)
        top1.pack(fill='x', padx=5, pady=5)
        tk.Button(top1, text="🔄 刷新", command=self._refresh_pending_approvals).pack(side='right')
        
        columns1 = ('id', 'project', 'applicant', 'cage', 'time', 'submit_time', 'node')
        self.pending_tree = ttk.Treeview(pending_frame, columns=columns1, show='headings')
        for col in columns1:
            self.pending_tree.heading(col, text=col)
        self.pending_tree.column('id', width=50)
        self.pending_tree.column('project', width=200)
        self.pending_tree.column('applicant', width=80)
        self.pending_tree.column('cage', width=100)
        self.pending_tree.column('time', width=200)
        self.pending_tree.column('submit_time', width=120)
        self.pending_tree.column('node', width=100)
        self.pending_tree.pack(fill='both', expand=True, padx=5)
        
        bottom1 = tk.Frame(pending_frame)
        bottom1.pack(fill='x', padx=5, pady=5)
        
        self.pending_detail = tk.Text(bottom1, height=5, font=('微软雅黑', 9))
        self.pending_detail.pack(side='left', fill='both', expand=True)
        self.pending_detail.config(state='disabled')
        
        btn_frame = tk.Frame(bottom1)
        btn_frame.pack(side='right', padx=10)
        
        self.approve_btn = tk.Button(btn_frame, text="✓ 通过", bg='#67c23a', fg='white', width=10, state='disabled', command=self._approve)
        self.approve_btn.pack(pady=5)
        self.reject_btn = tk.Button(btn_frame, text="✗ 驳回", bg='#f56c6c', fg='white', width=10, state='disabled', command=self._reject)
        self.reject_btn.pack(pady=5)
        
        self.pending_tree.bind('<<TreeviewSelect>>', self._on_pending_select)
        
        top2 = tk.Frame(history_frame)
        top2.pack(fill='x', padx=5, pady=5)
        tk.Button(top2, text="🔄 刷新", command=self._refresh_history_approvals).pack(side='right')
        
        columns2 = ('id', 'project', 'node', 'result', 'approver', 'time', 'comments', 'current_status')
        self.history_tree = ttk.Treeview(history_frame, columns=columns2, show='headings')
        for col in columns2:
            self.history_tree.heading(col, text=col)
        self.history_tree.column('id', width=50)
        self.history_tree.column('project', width=200)
        self.history_tree.column('node', width=100)
        self.history_tree.column('result', width=80)
        self.history_tree.column('approver', width=80)
        self.history_tree.column('time', width=120)
        self.history_tree.column('comments', width=150)
        self.history_tree.column('current_status', width=100)
        self.history_tree.pack(fill='both', expand=True, padx=5)
        
        notebook.bind('<<NotebookTabChanged>>', lambda e: self._refresh_approval_tab())

    def _refresh_approval_tab(self):
        self._refresh_pending_approvals()
        self._refresh_history_approvals()

    def _refresh_pending_approvals(self):
        for item in self.pending_tree.get_children():
            self.pending_tree.delete(item)
        
        approvals = ApprovalService.get_approvals_for_user(self.current_user.id)
        
        node_names = {'advisor': '导师审批', 'facility_manager': '管理员审批', 'ethics_committee': '伦理审批'}
        
        for approval in approvals:
            booking = approval.booking
            time_str = (f"{booking.start_time.strftime('%Y-%m-%d %H:%M')}\n"
                      f"{booking.end_time.strftime('%Y-%m-%d %H:%M')}")
            node_name = node_names.get(approval.node.value, approval.node.value)
            self.pending_tree.insert('', tk.END,
                values=(booking.id, booking.project_name, booking.researcher.name,
                       booking.cage.cage_code, time_str,
                       booking.created_at.strftime('%Y-%m-%d %H:%M'), node_name),
                tags=(approval.node.value,))

    def _refresh_history_approvals(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        from db.database import SessionLocal
        from models.approval import ApprovalStatus
        db = SessionLocal()
        try:
            approvals = db.query(Approval).filter(
                Approval.approver_id == self.current_user.id,
                Approval.status != ApprovalStatus.PENDING
            ).order_by(Approval.updated_at.desc()).all()
        finally:
            db.close()
        
        node_names = {'advisor': '导师审批', 'facility_manager': '管理员审批', 'ethics_committee': '伦理审批'}
        status_names = {'approved': '✓ 通过', 'rejected': '✗ 驳回'}
        
        for approval in approvals:
            booking = approval.booking
            node_name = node_names.get(approval.node.value, approval.node.value)
            status = status_names.get(approval.status.value, approval.status.value)
            self.history_tree.insert('', tk.END,
                values=(booking.id, booking.project_name, node_name, status,
                       approval.approver.name, approval.updated_at.strftime('%Y-%m-%d %H:%M'),
                       approval.comments or '无',
                       BookingService.get_booking_status_text(booking.status)))

    def _on_pending_select(self, event):
        selection = self.pending_tree.selection()
        if not selection:
            self.pending_detail.config(state='normal')
            self.pending_detail.delete('1.0', tk.END)
            self.pending_detail.config(state='disabled')
            self.approve_btn.config(state='disabled')
            self.reject_btn.config(state='disabled')
            return
            
        item = self.pending_tree.item(selection[0])
        booking_id = item['values'][0]
        booking = BookingService.get_booking_by_id(booking_id)
        
        detail = (f"📋 预约 #{booking.id}\n"
                 f"项目：{booking.project_name}\n"
                 f"申请人：{booking.researcher.name}\n"
                 f"笼位：{booking.cage.cage_code} ({booking.cage.room})\n"
                 f"动物：{booking.cage.animal_type} × {booking.animal_count}\n"
                 f"时段：{booking.start_time.strftime('%Y-%m-%d %H:%M')} 至 {booking.end_time.strftime('%Y-%m-%d %H:%M')}\n"
                 f"实验目的：{booking.purpose}")
        if booking.reject_reason:
            detail += f"\n\n⚠️ 上一步驳回原因：{booking.reject_reason}"
        
        self.pending_detail.config(state='normal')
        self.pending_detail.delete('1.0', tk.END)
        self.pending_detail.insert('1.0', detail)
        self.pending_detail.config(state='disabled')
        
        self.approve_btn.config(state='normal')
        self.reject_btn.config(state='normal')

    def _approve(self):
        selection = self.pending_tree.selection()
        if not selection:
            return
            
        item = self.pending_tree.item(selection[0])
        booking_id = item['values'][0]
        
        comments = simpledialog.askstring("审批意见", "请输入审批意见（可选）：", parent=self)
        if comments is None:
            return
            
        success, msg = ApprovalService.approve(booking_id, self.current_user.id, comments)
        if success:
            messagebox.showinfo("成功", msg)
            self._refresh_approval_tab()
            self._refresh_booking_tab()
        else:
            messagebox.showerror("失败", msg)

    def _reject(self):
        selection = self.pending_tree.selection()
        if not selection:
            return
            
        item = self.pending_tree.item(selection[0])
        booking_id = item['values'][0]
        
        reason = simpledialog.askstring("驳回原因", "请输入驳回原因（必填）：", parent=self)
        if not reason or not reason.strip():
            messagebox.showwarning("提示", "驳回时必须填写原因")
            return
            
        success, msg = ApprovalService.reject(booking_id, self.current_user.id, reason.strip())
        if success:
            messagebox.showinfo("成功", msg)
            self._refresh_approval_tab()
            self._refresh_booking_tab()
        else:
            messagebox.showerror("失败", msg)

    def _build_access_tab(self):
        frame = self.access_tab
        for widget in frame.winfo_children():
            widget.destroy()
        
        if self.current_user.role == UserRole.FACILITY_MANAGER:
            entry_frame = tk.LabelFrame(frame, text="快速登记", padding=10)
            entry_frame.pack(fill='x', padx=5, pady=5)
            
            tk.Label(entry_frame, text="准入码：").pack(side='left', padx=5)
            self.access_code_entry = tk.Entry(entry_frame, width=30, font=('微软雅黑', 11))
            self.access_code_entry.pack(side='left', padx=5)
            
            tk.Button(entry_frame, text="🚪 登记进入", bg='#67c23a', fg='white', command=self._record_entry).pack(side='left', padx=5)
            tk.Button(entry_frame, text="🚪 登记离开", bg='#e6a23c', fg='white', command=self._record_exit).pack(side='left', padx=5)
        
        notebook = ttk.Notebook(frame)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        pending_frame = tk.Frame(notebook)
        notebook.add(pending_frame, text='✅ 待准入（已通过审批）')
        
        active_frame = tk.Frame(notebook)
        notebook.add(active_frame, text='⏰ 进行中')
        
        history_frame = tk.Frame(notebook)
        notebook.add(history_frame, text='📜 历史记录')
        
        self._build_pending_access(pending_frame)
        self._build_active_access(active_frame)
        self._build_history_access(history_frame)

    def _build_pending_access(self, parent):
        frame = parent
        
        top = tk.Frame(frame)
        top.pack(fill='x', padx=5, pady=5)
        tk.Button(top, text="🔄 刷新", command=self._refresh_pending_access).pack(side='right')
        
        columns = ('id', 'project', 'applicant', 'cage', 'time', 'status', 'action', 'code')
        self.pending_access_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.pending_access_tree.heading('id', text='预约ID')
        self.pending_access_tree.heading('project', text='项目名称')
        self.pending_access_tree.heading('applicant', text='申请人')
        self.pending_access_tree.heading('cage', text='笼位')
        self.pending_access_tree.heading('time', text='时段')
        self.pending_access_tree.heading('status', text='状态')
        self.pending_access_tree.heading('action', text='操作')
        self.pending_access_tree.heading('code', text='准入码')
        self.pending_access_tree.column('id', width=70)
        self.pending_access_tree.column('project', width=200)
        self.pending_access_tree.column('applicant', width=80)
        self.pending_access_tree.column('cage', width=120)
        self.pending_access_tree.column('time', width=200)
        self.pending_access_tree.column('status', width=80)
        self.pending_access_tree.column('action', width=100)
        self.pending_access_tree.column('code', width=120)
        self.pending_access_tree.pack(fill='both', expand=True, padx=5)
        
        self.pending_access_tree.bind('<Double-1>', self._on_access_double_click)

    def _build_active_access(self, parent):
        frame = parent
        
        top = tk.Frame(frame)
        top.pack(fill='x', padx=5, pady=5)
        self.active_count_label = tk.Label(top, text="当前场内人员：0 人", fg='#e6a23c', font=('微软雅黑', 10, 'bold'))
        self.active_count_label.pack(side='left')
        tk.Button(top, text="🔄 刷新", command=self._refresh_active_access).pack(side='right')
        
        columns = ('code', 'booking_id', 'applicant', 'cage', 'entry_time', 'registrar', 'action')
        self.active_access_tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            self.active_access_tree.heading(col, text=col)
        self.active_access_tree.column('code', width=120)
        self.active_access_tree.column('booking_id', width=70)
        self.active_access_tree.column('applicant', width=80)
        self.active_access_tree.column('cage', width=100)
        self.active_access_tree.column('entry_time', width=140)
        self.active_access_tree.column('registrar', width=80)
        self.active_access_tree.column('action', width=100)
        self.active_access_tree.pack(fill='both', expand=True, padx=5)
        
        self.active_access_tree.bind('<Double-1>', self._on_active_double_click)

    def _build_history_access(self, parent):
        frame = parent
        
        top = tk.Frame(frame)
        top.pack(fill='x', padx=5, pady=5)
        tk.Button(top, text="🔄 刷新", command=self._refresh_history_access).pack(side='right')
        
        columns = ('code', 'booking_id', 'applicant', 'cage', 'entry_time', 'exit_time', 'duration', 'registrar')
        self.history_access_tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            self.history_access_tree.heading(col, text=col)
        self.history_access_tree.column('code', width=120)
        self.history_access_tree.column('booking_id', width=70)
        self.history_access_tree.column('applicant', width=80)
        self.history_access_tree.column('cage', width=100)
        self.history_access_tree.column('entry_time', width=140)
        self.history_access_tree.column('exit_time', width=140)
        self.history_access_tree.column('duration', width=80)
        self.history_access_tree.column('registrar', width=80)
        self.history_access_tree.pack(fill='both', expand=True, padx=5)

    def _refresh_access_tab(self):
        self._refresh_pending_access()
        self._refresh_active_access()
        self._refresh_history_access()

    def _refresh_pending_access(self):
        for item in self.pending_access_tree.get_children():
            self.pending_access_tree.delete(item)
        
        bookings = BookingService.get_bookings_by_status(BookingStatus.APPROVED)
        
        for booking in bookings:
            access = AccessService.get_access_by_booking(booking.id)
            if access and access.is_active:
                continue
            
            time_str = (f"{booking.start_time.strftime('%Y-%m-%d %H:%M')}\n"
                      f"{booking.end_time.strftime('%Y-%m-%d %H:%M')}")
            status = BookingService.get_booking_status_text(booking.status)
            action = "生成准入码" if self.current_user.role == UserRole.FACILITY_MANAGER else "-"
            code = access.access_code if access else "未生成"
            
            self.pending_access_tree.insert('', tk.END,
                values=(booking.id, booking.project_name, booking.researcher.name,
                       f"{booking.cage.cage_code} ({booking.cage.room})",
                       time_str, status, action, code))

    def _refresh_active_access(self):
        for item in self.active_access_tree.get_children():
            self.active_access_tree.delete(item)
        
        access_list = AccessService.get_active_access_registrations()
        self.active_count_label.config(text=f"当前场内人员：{len(access_list)} 人")
        
        for access in access_list:
            booking = access.booking
            entry_time = access.entry_time.strftime('%Y-%m-%d %H:%M') if access.entry_time else '-'
            action = "登记离开" if (self.current_user.role == UserRole.FACILITY_MANAGER and access.entry_time and not access.exit_time) else "-"
            
            self.active_access_tree.insert('', tk.END,
                values=(access.access_code, booking.id, booking.researcher.name,
                       booking.cage.cage_code, entry_time, access.registered_by, action))

    def _refresh_history_access(self):
        for item in self.history_access_tree.get_children():
            self.history_access_tree.delete(item)
        
        access_list = AccessService.get_all_access_registrations()
        
        for access in access_list:
            if access.is_active and not access.exit_time:
                continue
            
            booking = access.booking
            entry_time = access.entry_time.strftime('%Y-%m-%d %H:%M') if access.entry_time else '-'
            exit_time = access.exit_time.strftime('%Y-%m-%d %H:%M') if access.exit_time else '-'
            
            duration = '-'
            if access.entry_time and access.exit_time:
                hours = (access.exit_time - access.entry_time).total_seconds() / 3600
                duration = f"{hours:.1f} 小时"
            
            self.history_access_tree.insert('', tk.END,
                values=(access.access_code, booking.id, booking.researcher.name,
                       booking.cage.cage_code, entry_time, exit_time, duration, access.registered_by))

    def _on_access_double_click(self, event):
        if self.current_user.role != UserRole.FACILITY_MANAGER:
            return
            
        item = self.pending_access_tree.identify('item', event.x, event.y)
        if not item:
            return
            
        values = self.pending_access_tree.item(item)['values']
        booking_id = values[0]
        
        if messagebox.askyesno("确认", f"确定要为预约 #{booking_id} 生成准入码吗？"):
            success, msg, access = AccessService.create_access_registration(booking_id, self.current_user.name)
            if success:
                messagebox.showinfo("成功", f"准入码生成成功！\n\n准入码：{access.access_code}\n\n请告知申请人。")
                self._refresh_pending_access()
            else:
                messagebox.showerror("失败", msg)

    def _on_active_double_click(self, event):
        if self.current_user.role != UserRole.FACILITY_MANAGER:
            return
            
        item = self.active_access_tree.identify('item', event.x, event.y)
        if not item:
            return
            
        values = self.active_access_tree.item(item)['values']
        access_code = values[0]
        action = values[6]
        
        if action == "登记离开":
            if messagebox.askyesno("确认", f"确定要登记 {access_code} 离开吗？"):
                success, msg = AccessService.record_exit(access_code)
                if success:
                    messagebox.showinfo("成功", msg)
                    self._refresh_active_access()
                    self._refresh_history_access()
                    self._refresh_booking_tab()
                else:
                    messagebox.showerror("失败", msg)

    def _record_entry(self):
        code = self.access_code_entry.get().strip()
        if not code:
            messagebox.showwarning("提示", "请输入准入码")
            return
            
        success, msg = AccessService.record_entry(code)
        if success:
            messagebox.showinfo("成功", msg)
            self.access_code_entry.delete(0, tk.END)
            self._refresh_access_tab()
        else:
            messagebox.showwarning("失败", msg)

    def _record_exit(self):
        code = self.access_code_entry.get().strip()
        if not code:
            messagebox.showwarning("提示", "请输入准入码")
            return
            
        success, msg = AccessService.record_exit(code)
        if success:
            messagebox.showinfo("成功", msg)
            self.access_code_entry.delete(0, tk.END)
            self._refresh_access_tab()
            self._refresh_booking_tab()
        else:
            messagebox.showwarning("失败", msg)

if __name__ == '__main__':
    app = AnimalLabApp()
    app.mainloop()
