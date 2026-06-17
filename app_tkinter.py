import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta, date, time as dt_time
from db.database import init_db, create_sample_data
from models.user import UserRole
from models.booking import BookingStatus
from services.user_service import UserService
from services.cage_service import CageService
from services.booking_service import BookingService
from services.conflict_service import ConflictService
from services.approval_service import ApprovalService
from services.access_service import AccessService


def safe_get(obj, *attrs, default='-'):
    try:
        result = obj
        for attr in attrs:
            if result is None:
                return default
            result = getattr(result, attr, None)
        return result if result is not None else default
    except Exception:
        return default


class AnimalLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("实验动物房预约管理系统")
        self.geometry("1280x750")
        self.minsize(1000, 600)
        self.current_user = None

        try:
            style = ttk.Style(self)
            if 'clam' in style.theme_names():
                style.theme_use('clam')
        except Exception:
            pass

        try:
            init_db()
            create_sample_data()
        except Exception as e:
            messagebox.showerror("初始化失败", f"数据库初始化失败：{str(e)}\n\n{traceback.format_exc()}")
            sys.exit(1)

        self._show_login()

    def _show_login(self):
        for widget in self.winfo_children():
            widget.destroy()

        login_frame = tk.Frame(self, padx=60, pady=50)
        login_frame.pack(expand=True, fill='both')

        tk.Label(login_frame, text="🔬 实验动物房预约管理系统",
                 font=('Microsoft YaHei UI', 22, 'bold'),
                 fg='#2c3e50').pack(pady=(0, 8))
        tk.Label(login_frame, text="Laboratory Animal Room Booking System",
                 font=('Microsoft YaHei UI', 9), fg='#95a5a6').pack(pady=(0, 30))

        box = tk.Frame(login_frame, padx=40, pady=30, bg='#f8f9fa',
                       highlightbackground='#dee2e6', highlightthickness=1)
        box.pack(expand=True)

        tk.Label(box, text="账号登录", font=('Microsoft YaHei UI', 14, 'bold'),
                 bg='#f8f9fa', fg='#2c3e50').pack(pady=(0, 20))

        form = tk.Frame(box, bg='#f8f9fa')
        form.pack(fill='x')

        tk.Label(form, text="用户名", font=('Microsoft YaHei UI', 10),
                 bg='#f8f9fa').grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.username_entry = ttk.Entry(form, font=('Microsoft YaHei UI', 11), width=28)
        self.username_entry.grid(row=1, column=0, pady=(0, 15))
        self.username_entry.insert(0, 'student1')
        self.username_entry.focus()

        tk.Label(form, text="密码", font=('Microsoft YaHei UI', 10),
                 bg='#f8f9fa').grid(row=2, column=0, sticky='w', pady=(0, 5))
        self.password_entry = ttk.Entry(form, show='*', font=('Microsoft YaHei UI', 11), width=28)
        self.password_entry.grid(row=3, column=0, pady=(0, 15))
        self.password_entry.insert(0, '123456')

        tk.Label(box, text="测试账号：student1 / advisor1 / manager1 / ethics1  |  密码：123456",
                 font=('Microsoft YaHei UI', 8), fg='#adb5bd', bg='#f8f9fa',
                 wraplength=300, justify='center').pack(pady=(0, 15))

        login_btn = tk.Button(box, text="登  录", font=('Microsoft YaHei UI', 12, 'bold'),
                              bg='#3498db', fg='white', width=22, height=1,
                              activebackground='#2980b9', activeforeground='white',
                              relief='flat', cursor='hand2', command=self._on_login)
        login_btn.pack(pady=5)

        self.bind('<Return>', lambda e: self._on_login())

        tk.Label(login_frame, text="© 2026 科研机构动物实验中心",
                 font=('Microsoft YaHei UI', 8), fg='#adb5bd').pack(pady=(30, 0))

    def _on_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("提示", "请输入用户名和密码")
            return

        try:
            success, user, msg = UserService.authenticate(username, password)
            if success:
                self.current_user = user
                self._build_main_ui()
            else:
                messagebox.showerror("登录失败", msg)
        except Exception as e:
            messagebox.showerror("登录异常", f"登录时发生错误：{str(e)}\n\n{traceback.format_exc()}")

    def _build_main_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        header = tk.Frame(self, bg='#2c3e50', height=64)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="🐭 实验动物房预约管理系统",
                 bg='#2c3e50', fg='white',
                 font=('Microsoft YaHei UI', 15, 'bold')).pack(side='left', padx=24, pady=15)

        right_header = tk.Frame(header, bg='#2c3e50')
        right_header.pack(side='right', padx=10, pady=15)

        role_name = UserService.get_role_name(self.current_user.role)
        tk.Label(right_header, text=f"👤 {self.current_user.name}",
                 bg='#2c3e50', fg='#ecf0f1',
                 font=('Microsoft YaHei UI', 10)).pack(side='left', padx=5)
        tk.Label(right_header, text=f"| {role_name}",
                 bg='#2c3e50', fg='#95a5a6',
                 font=('Microsoft YaHei UI', 9)).pack(side='left', padx=5)

        tk.Button(right_header, text="切换账号", bg='#34495e', fg='white',
                  relief='flat', padx=14, pady=4, cursor='hand2',
                  activebackground='#4a6785', activeforeground='white',
                  font=('Microsoft YaHei UI', 9), command=self._logout).pack(side='left', padx=10)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=12, pady=12)

        try:
            self.cage_tab = tk.Frame(self.notebook)
            self.booking_tab = tk.Frame(self.notebook)
            self.approval_tab = tk.Frame(self.notebook)
            self.access_tab = tk.Frame(self.notebook)

            self.notebook.add(self.cage_tab, text='  🏠 笼位排期  ')
            self.notebook.add(self.booking_tab, text='  📋 我的预约  ')
            self.notebook.add(self.approval_tab, text='  ✅ 审批管理  ')
            self.notebook.add(self.access_tab, text='  🔐 准入登记  ')

            self._build_cage_tab()
            self._build_booking_tab()
            self._build_approval_tab()
            self._build_access_tab()

            self._safe_refresh(self._refresh_cage_tab)
            self._safe_refresh(self._refresh_booking_tab)
            self._safe_refresh(self._refresh_approval_tab)
            self._safe_refresh(self._refresh_access_tab)
        except Exception as e:
            messagebox.showerror("界面初始化失败", f"模块加载异常：{str(e)}\n\n{traceback.format_exc()}")

    def _logout(self):
        if messagebox.askyesno("确认", "确定要切换账号吗？"):
            self.current_user = None
            self._show_login()

    def _safe_refresh(self, func):
        try:
            func()
        except Exception as e:
            print(f"[刷新错误] {func.__name__}: {str(e)}")
            traceback.print_exc()

    # ==================== 笼位排期模块 ====================
    def _build_cage_tab(self):
        frame = self.cage_tab
        for widget in frame.winfo_children():
            widget.destroy()

        main_paned = tk.PanedWindow(frame, orient='horizontal', sashwidth=4)
        main_paned.pack(fill='both', expand=True, padx=8, pady=8)

        left_frame = tk.Frame(main_paned, width=280)
        main_paned.add(left_frame, minsize=220)

        lheader = tk.Frame(left_frame)
        lheader.pack(fill='x', pady=(0, 6))
        tk.Label(lheader, text="笼位列表", font=('Microsoft YaHei UI', 11, 'bold')).pack(side='left')

        btn_row = tk.Frame(left_frame)
        btn_row.pack(fill='x', pady=(0, 6))
        tk.Button(btn_row, text="🔄", width=3, command=lambda: self._safe_refresh(self._refresh_cage_tab)).pack(side='left', padx=2)
        if self.current_user.role == UserRole.FACILITY_MANAGER:
            tk.Button(btn_row, text="➕ 新增", bg='#409eff', fg='white',
                      relief='flat', font=('Microsoft YaHei UI', 9),
                      command=self._add_cage_dialog).pack(side='left', padx=4)

        list_frame = tk.Frame(left_frame, bg='#f1f3f5')
        list_frame.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        self.cage_listbox = tk.Listbox(list_frame, font=('Microsoft YaHei UI', 10),
                                       activestyle='dotbox', selectbackground='#409eff',
                                       selectforeground='white', relief='flat',
                                       yscrollcommand=scrollbar.set)
        self.cage_listbox.pack(fill='both', expand=True, padx=1, pady=1)
        scrollbar.config(command=self.cage_listbox.yview)
        self.cage_listbox.bind('<<ListboxSelect>>', lambda e: self._safe_refresh(self._on_cage_select))

        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame)

        ctrl_frame = tk.Frame(right_frame)
        ctrl_frame.pack(fill='x', pady=(0, 8))

        tk.Label(ctrl_frame, text="排期日期：", font=('Microsoft YaHei UI', 10)).pack(side='left', padx=4)
        self.cage_date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        self.cage_date_entry = ttk.Entry(ctrl_frame, textvariable=self.cage_date_var, width=12,
                                         font=('Microsoft YaHei UI', 10))
        self.cage_date_entry.pack(side='left')
        tk.Button(ctrl_frame, text="◀", width=3, command=self._cage_prev_day).pack(side='left', padx=2)
        tk.Button(ctrl_frame, text="▶", width=3, command=self._cage_next_day).pack(side='left', padx=2)
        tk.Button(ctrl_frame, text="今天", width=6, command=self._cage_today).pack(side='left', padx=2)

        if self.current_user.role == UserRole.RESEARCHER:
            tk.Button(ctrl_frame, text="📅 新建预约", bg='#67c23a', fg='white',
                      relief='flat', font=('Microsoft YaHei UI', 10, 'bold'),
                      padx=12, pady=4, command=self._create_booking_dialog).pack(side='right')

        tk.Label(right_frame, text="⏰ 时段排期表", font=('Microsoft YaHei UI', 11, 'bold')).pack(anchor='w', pady=(8, 4))

        columns = ('time', 'info', 'status')
        self.cage_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=18)
        self.cage_tree.heading('time', text='时段')
        self.cage_tree.heading('info', text='预约信息')
        self.cage_tree.heading('status', text='状态')
        self.cage_tree.column('time', width=110, anchor='center')
        self.cage_tree.column('info', width=450)
        self.cage_tree.column('status', width=100, anchor='center')

        self.cage_tree.tag_configure('available', background='#f0f9eb')
        self.cage_tree.tag_configure('pending', background='#fdf6ec')
        self.cage_tree.tag_configure('approved', background='#fef0f0')

        tree_scroll = ttk.Scrollbar(right_frame, orient='vertical', command=self.cage_tree.yview)
        self.cage_tree.configure(yscrollcommand=tree_scroll.set)

        tree_container = tk.Frame(right_frame)
        tree_container.pack(fill='both', expand=True)
        self.cage_tree.pack(side='left', fill='both', expand=True)
        tree_scroll.pack(side='right', fill='y')

        self.selected_cage = None
        self.cages = []

    def _refresh_cage_tab(self):
        self.cage_listbox.delete(0, tk.END)
        cages = CageService.get_all_cages()
        self.cages = cages
        status_icons = {'available': '🟢', 'occupied': '🔴', 'maintenance': '🟡'}
        for cage in cages:
            icon = status_icons.get(cage.status.value, '⚪')
            self.cage_listbox.insert(tk.END,
                f"{icon} [{cage.cage_code}] {cage.room}")
            idx = self.cage_listbox.size() - 1
            self.cage_listbox.insert(tk.END,
                f"     {cage.animal_type} · 容量{cage.capacity}")
            self.cage_listbox.itemconfig(tk.END, fg='#868e96')

        if self.cages and not self.selected_cage:
            self.cage_listbox.selection_set(0)
            self.selected_cage = self.cages[0]

        self._safe_refresh(self._refresh_cage_schedule)

    def _on_cage_select(self):
        selection = self.cage_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        cage_idx = idx // 2 if idx < len(self.cages) * 2 else 0
        if cage_idx < len(self.cages):
            self.selected_cage = self.cages[cage_idx]
            self._safe_refresh(self._refresh_cage_schedule)

    def _cage_prev_day(self):
        try:
            d = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
            self.cage_date_var.set((d - timedelta(days=1)).strftime('%Y-%m-%d'))
            self._safe_refresh(self._refresh_cage_schedule)
        except Exception: pass

    def _cage_next_day(self):
        try:
            d = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
            self.cage_date_var.set((d + timedelta(days=1)).strftime('%Y-%m-%d'))
            self._safe_refresh(self._refresh_cage_schedule)
        except Exception: pass

    def _cage_today(self):
        self.cage_date_var.set(date.today().strftime('%Y-%m-%d'))
        self._safe_refresh(self._refresh_cage_schedule)

    def _refresh_cage_schedule(self):
        for item in self.cage_tree.get_children():
            self.cage_tree.delete(item)

        if not self.selected_cage:
            return

        try:
            sel_date = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
        except Exception:
            sel_date = date.today()

        start_dt = datetime.combine(sel_date, dt_time.min)
        end_dt = datetime.combine(sel_date + timedelta(days=1), dt_time.min)

        try:
            bookings = ConflictService.get_cage_bookings_in_range(
                self.selected_cage.id, start_dt, end_dt
            )
        except Exception:
            bookings = []

        for hour in range(8, 20):
            slot_start = datetime.combine(sel_date, dt_time(hour, 0))
            slot_end = datetime.combine(sel_date, dt_time(hour + 1, 0))
            time_str = f"{slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}"

            info = '（可预约）'
            status = '空闲'
            tag = 'available'

            for booking in bookings:
                try:
                    if ConflictService.check_time_overlap(slot_start, slot_end,
                                                          booking.start_time, booking.end_time):
                        if booking.status not in [BookingStatus.REJECTED, BookingStatus.CANCELLED]:
                            proj = safe_get(booking, 'project_name', default='')
                            rname = safe_get(booking, 'researcher', 'name', default='')
                            st = safe_get(booking, 'start_time')
                            et = safe_get(booking, 'end_time')
                            if isinstance(st, datetime): st = st.strftime('%H:%M')
                            if isinstance(et, datetime): et = et.strftime('%H:%M')

                            info = f"#{booking.id} {proj}\n申请人：{rname} | {st}-{et}"
                            status = BookingService.get_booking_status_text(booking.status)
                            tag = 'pending' if '待' in status else 'approved'
                            break
                except Exception:
                    continue

            self.cage_tree.insert('', tk.END, values=(time_str, info, status), tags=(tag,))

    def _add_cage_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("新增笼位")
        dlg.geometry("420x380")
        dlg.transient(self)
        dlg.grab_set()

        form = tk.Frame(dlg, padx=25, pady=20)
        form.pack(fill='both', expand=True)
        tk.Label(form, text="新增笼位信息", font=('Microsoft YaHei UI', 12, 'bold')).pack(pady=(0, 15))

        entries = {}
        fields = [("笼位编号 *", 'cage_code'), ("所在房间 *", 'room'),
                  ("容纳数量", 'capacity'), ("动物类型 *", 'animal_type')]
        for label, key in fields:
            row = tk.Frame(form)
            row.pack(fill='x', pady=4)
            tk.Label(row, text=label, font=('Microsoft YaHei UI', 10), width=12, anchor='e').pack(side='left')
            if key == 'capacity':
                entry = tk.Spinbox(row, from_=1, to=100, width=28, font=('Microsoft YaHei UI', 10))
                entry.delete(0, tk.END)
                entry.insert(0, '5')
            else:
                entry = ttk.Entry(row, width=30, font=('Microsoft YaHei UI', 10))
            entry.pack(side='left', padx=6)
            entries[key] = entry

        row = tk.Frame(form)
        row.pack(fill='x', pady=4)
        tk.Label(row, text="备注说明", font=('Microsoft YaHei UI', 10), width=12, anchor='ne').pack(side='left')
        desc_text = tk.Text(row, width=30, height=4, font=('Microsoft YaHei UI', 10))
        desc_text.pack(side='left', padx=6)

        def save():
            try:
                data = {}
                for k, v in entries.items():
                    val = v.get().strip() if not isinstance(v, tk.Spinbox) else v.get()
                    data[k] = int(val) if k == 'capacity' else val
                data['description'] = desc_text.get('1.0', tk.END).strip()

                if not all([data.get('cage_code'), data.get('room'), data.get('animal_type')]):
                    messagebox.showwarning("提示", "请填写所有必填项（带*）", parent=dlg)
                    return

                success, msg, _ = CageService.create_cage(**data)
                if success:
                    messagebox.showinfo("成功", msg, parent=dlg)
                    dlg.destroy()
                    self._safe_refresh(self._refresh_cage_tab)
                else:
                    messagebox.showerror("失败", msg, parent=dlg)
            except Exception as e:
                messagebox.showerror("错误", f"操作失败：{str(e)}", parent=dlg)

        btn_row = tk.Frame(form)
        btn_row.pack(pady=18)
        tk.Button(btn_row, text="确定保存", bg='#67c23a', fg='white', width=12,
                  relief='flat', font=('Microsoft YaHei UI', 10, 'bold'), command=save).pack(side='left', padx=8)
        tk.Button(btn_row, text="取消", width=12, relief='flat',
                  font=('Microsoft YaHei UI', 10), command=dlg.destroy).pack(side='left', padx=8)

    def _create_booking_dialog(self):
        if not self.selected_cage:
            messagebox.showwarning("提示", "请先在左侧选择一个笼位")
            return
        self._edit_booking_dialog(None, is_new=True, cage=self.selected_cage)

    # ==================== 我的预约模块 ====================
    def _build_booking_tab(self):
        frame = self.booking_tab
        for widget in frame.winfo_children():
            widget.destroy()

        top = tk.Frame(frame)
        top.pack(fill='x', padx=8, pady=8)

        tk.Label(top, text="状态筛选：", font=('Microsoft YaHei UI', 10)).pack(side='left', padx=4)
        self.booking_filter_var = tk.StringVar(value="全部")
        status_list = ["全部"] + [BookingService.get_booking_status_text(s) for s in BookingStatus]
        filter_combo = ttk.Combobox(top, textvariable=self.booking_filter_var, values=status_list,
                                   width=15, state='readonly', font=('Microsoft YaHei UI', 10))
        filter_combo.pack(side='left')
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self._safe_refresh(self._refresh_booking_tab))

        tk.Button(top, text="🔄 刷新列表", command=lambda: self._safe_refresh(self._refresh_booking_tab)).pack(side='right')

        columns = ('id', 'project', 'cage', 'time', 'count', 'status', 'reason')
        self.booking_tree = ttk.Treeview(frame, columns=columns, show='headings', height=12)
        headers = [('id', 'ID', 55), ('project', '项目名称', 220), ('cage', '笼位', 140),
                   ('time', '预约时段', 260), ('count', '数量', 55),
                   ('status', '状态', 110), ('reason', '驳回原因', 180)]
        for col, text, w in headers:
            self.booking_tree.heading(col, text=text)
            self.booking_tree.column(col, width=w, anchor='w' if col in ['project', 'time', 'reason'] else 'center')

        bscroll = ttk.Scrollbar(frame, orient='vertical', command=self.booking_tree.yview)
        self.booking_tree.configure(yscrollcommand=bscroll.set)

        tcontainer = tk.Frame(frame)
        tcontainer.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.booking_tree.pack(side='left', fill='both', expand=True)
        bscroll.pack(side='right', fill='y')

        self.booking_tree.bind('<<TreeviewSelect>>', lambda e: self._safe_refresh(self._on_booking_select))

        bottom = tk.LabelFrame(frame, text=" 预约详情与操作 ", padx=10, pady=8, font=('Microsoft YaHei UI', 10))
        bottom.pack(fill='x', padx=8, pady=(0, 8))

        self.booking_detail = tk.Text(bottom, height=5, font=('Microsoft YaHei UI', 9),
                                      relief='flat', bg='#f8f9fa')
        self.booking_detail.pack(fill='x', pady=(0, 8))
        self.booking_detail.config(state='disabled')

        btn_bar = tk.Frame(bottom)
        btn_bar.pack(fill='x')

        self.edit_btn = tk.Button(btn_bar, text="✏️ 修改预约", state='disabled',
                                  command=self._edit_current_booking,
                                  bg='#409eff', fg='white', relief='flat',
                                  font=('Microsoft YaHei UI', 10), padx=12, pady=5)
        self.edit_btn.pack(side='left', padx=4)

        self.submit_btn = tk.Button(btn_bar, text="📤 提交审批", state='disabled',
                                    command=self._submit_current_booking,
                                    bg='#e6a23c', fg='white', relief='flat',
                                    font=('Microsoft YaHei UI', 10, 'bold'), padx=12, pady=5)
        self.submit_btn.pack(side='left', padx=4)

        self.cancel_btn = tk.Button(btn_bar, text="❌ 取消预约", state='disabled',
                                    command=self._cancel_current_booking,
                                    bg='#f56c6c', fg='white', relief='flat',
                                    font=('Microsoft YaHei UI', 10), padx=12, pady=5)
        self.cancel_btn.pack(side='left', padx=4)

        self.history_btn = tk.Button(btn_bar, text="📜 审批记录", state='disabled',
                                     command=self._view_approval_history,
                                     relief='flat', font=('Microsoft YaHei UI', 10), padx=12, pady=5)
        self.history_btn.pack(side='left', padx=4)

        self._current_booking_id = None

    def _refresh_booking_tab(self):
        for item in self.booking_tree.get_children():
            self.booking_tree.delete(item)

        try:
            if self.current_user.role == UserRole.RESEARCHER:
                bookings = BookingService.get_bookings_by_researcher(self.current_user.id)
            else:
                bookings = BookingService.get_all_bookings()
        except Exception as e:
            print(f"加载预约列表失败: {e}")
            return

        filter_text = self.booking_filter_var.get()
        if filter_text != "全部":
            bookings = [b for b in bookings
                       if BookingService.get_booking_status_text(b.status) == filter_text]

        for booking in bookings:
            try:
                st = safe_get(booking, 'start_time')
                et = safe_get(booking, 'end_time')
                if isinstance(st, datetime): st = st.strftime('%Y-%m-%d %H:%M')
                if isinstance(et, datetime): et = et.strftime('%Y-%m-%d %H:%M')

                cage_code = safe_get(booking, 'cage', 'cage_code', default='-')
                cage_room = safe_get(booking, 'cage', 'room', default='')
                cage_str = f"{cage_code} ({cage_room})" if cage_room else cage_code

                self.booking_tree.insert('', tk.END, iid=str(booking.id),
                    values=(
                        booking.id,
                        safe_get(booking, 'project_name', default=''),
                        cage_str,
                        f"{st}\n{et}",
                        safe_get(booking, 'animal_count', default=''),
                        BookingService.get_booking_status_text(booking.status),
                        safe_get(booking, 'reject_reason', default='') or '-'
                    ),
                    tags=(booking.status.value,))
            except Exception as e:
                print(f"渲染预约#{safe_get(booking, 'id', default='?')}失败: {e}")
                continue

    def _on_booking_select(self):
        selection = self.booking_tree.selection()
        detail_text = "请在上方列表中选择一条预约记录查看详情"
        can_edit = False
        can_submit = False
        can_cancel = False
        can_history = False
        self._current_booking_id = None

        if selection:
            try:
                booking_id = int(selection[0])
                booking = BookingService.get_booking_by_id(booking_id)
                if booking:
                    self._current_booking_id = booking_id

                    st = safe_get(booking, 'start_time')
                    et = safe_get(booking, 'end_time')
                    if isinstance(st, datetime): st = st.strftime('%Y-%m-%d %H:%M')
                    if isinstance(et, datetime): et = et.strftime('%Y-%m-%d %H:%M')

                    cage_code = safe_get(booking, 'cage', 'cage_code', default='-')
                    cage_room = safe_get(booking, 'cage', 'room', default='')
                    rname = safe_get(booking, 'researcher', 'name', default='-')
                    atype = safe_get(booking, 'cage', 'animal_type', default='')

                    detail_text = (
                        f"📋 预约编号：#{booking.id}\n"
                        f"📝 项目名称：{safe_get(booking, 'project_name', default='')}\n"
                        f"🏠 笼位信息：{cage_code} - {cage_room}（{atype}）\n"
                        f"🔢 动物数量：{safe_get(booking, 'animal_count', default='')} 只\n"
                        f"⏰ 使用时段：{st} 至 {et}\n"
                        f"👤 申请人员：{rname}\n"
                        f"📌 当前状态：{BookingService.get_booking_status_text(booking.status)}\n"
                        f"📄 实验目的：{safe_get(booking, 'purpose', default='')}"
                    )
                    reject_reason = safe_get(booking, 'reject_reason')
                    if reject_reason:
                        detail_text += f"\n⚠️ 驳回原因：{reject_reason}"

                    is_researcher = self.current_user.role == UserRole.RESEARCHER
                    is_own = (safe_get(booking, 'researcher', 'id') == self.current_user.id)

                    can_edit = (is_researcher and is_own and booking.status == BookingStatus.DRAFT)
                    can_submit = (is_researcher and is_own and booking.status == BookingStatus.DRAFT)
                    can_cancel = (is_researcher and is_own and booking.status not in
                                  [BookingStatus.CANCELLED, BookingStatus.REJECTED, BookingStatus.COMPLETED])

                    try:
                        approvals = booking.approvals
                        can_history = (approvals and len(approvals) > 0)
                    except Exception:
                        can_history = False
            except Exception as e:
                detail_text = f"加载详情失败：{str(e)}"

        self.booking_detail.config(state='normal')
        self.booking_detail.delete('1.0', tk.END)
        self.booking_detail.insert('1.0', detail_text)
        self.booking_detail.config(state='disabled')

        self.edit_btn.config(state='normal' if can_edit else 'disabled')
        self.submit_btn.config(state='normal' if can_submit else 'disabled')
        self.cancel_btn.config(state='normal' if can_cancel else 'disabled')
        self.history_btn.config(state='normal' if can_history else 'disabled')

    def _edit_current_booking(self):
        if not self._current_booking_id:
            return
        booking = BookingService.get_booking_by_id(self._current_booking_id)
        if booking:
            self._edit_booking_dialog(booking, is_new=False)

    def _edit_booking_dialog(self, booking, is_new=True, cage=None):
        dlg = tk.Toplevel(self)
        dlg.title(("新建" if is_new else "修改") + "预约")
        dlg.geometry("500x560")
        dlg.transient(self)
        dlg.grab_set()

        form = tk.Frame(dlg, padx=25, pady=15)
        form.pack(fill='both', expand=True)
        tk.Label(form, text=("📅 新建" if is_new else "✏️ 修改") + "预约申请",
                 font=('Microsoft YaHei UI', 13, 'bold')).pack(pady=(0, 12))

        if is_new and cage:
            info = tk.LabelFrame(form, text=" 基础信息 ", padx=10, pady=6, font=('Microsoft YaHei UI', 9))
            info.pack(fill='x', pady=(0, 8))
            tk.Label(info, text=f"笼位：{cage.cage_code}（{cage.room}）- {cage.animal_type}",
                     font=('Microsoft YaHei UI', 10)).pack(anchor='w')
            tk.Label(info, text=f"申请人：{self.current_user.name}",
                     font=('Microsoft YaHei UI', 10)).pack(anchor='w')

        fields_frame = tk.LabelFrame(form, text=" 预约内容 ", padx=12, pady=10, font=('Microsoft YaHei UI', 9))
        fields_frame.pack(fill='both', expand=True)

        entries = {}

        tk.Label(fields_frame, text="项目名称 *", font=('Microsoft YaHei UI', 10)).grid(row=0, column=0, sticky='e', pady=6, padx=4)
        e = ttk.Entry(fields_frame, width=32, font=('Microsoft YaHei UI', 10))
        e.grid(row=0, column=1, pady=6)
        if not is_new: e.insert(0, safe_get(booking, 'project_name', default=''))
        entries['project_name'] = e

        max_count = cage.capacity if (is_new and cage) else safe_get(booking, 'cage', 'capacity', default=20)
        tk.Label(fields_frame, text=f"动物数量(1-{max_count}) *", font=('Microsoft YaHei UI', 10)).grid(row=1, column=0, sticky='e', pady=6, padx=4)
        spin = tk.Spinbox(fields_frame, from_=1, to=max_count, width=30, font=('Microsoft YaHei UI', 10))
        spin.grid(row=1, column=1, pady=6)
        if not is_new:
            spin.delete(0, tk.END)
            spin.insert(0, str(safe_get(booking, 'animal_count', default=1)))
        entries['animal_count'] = spin

        try:
            if is_new and cage:
                sel_date = datetime.strptime(self.cage_date_var.get(), '%Y-%m-%d').date()
            else:
                sel_date = safe_get(booking, 'start_time')
                if isinstance(sel_date, datetime):
                    sel_date = sel_date.date()
                else:
                    sel_date = date.today()
        except Exception:
            sel_date = date.today()

        tk.Label(fields_frame, text="预约日期 *", font=('Microsoft YaHei UI', 10)).grid(row=2, column=0, sticky='e', pady=6, padx=4)
        date_e = ttk.Entry(fields_frame, width=32, font=('Microsoft YaHei UI', 10))
        date_e.grid(row=2, column=1, pady=6)
        date_e.insert(0, sel_date.strftime('%Y-%m-%d'))
        tk.Label(fields_frame, text="格式：YYYY-MM-DD", fg='#868e96',
                 font=('Microsoft YaHei UI', 8)).grid(row=2, column=2, sticky='w', padx=4)
        entries['date'] = date_e

        st_h, st_m = 9, 0
        et_h, et_m = 12, 0
        if not is_new:
            st = safe_get(booking, 'start_time')
            et = safe_get(booking, 'end_time')
            if isinstance(st, datetime): st_h, st_m = st.hour, st.minute
            if isinstance(et, datetime): et_h, et_m = et.hour, et.minute

        tk.Label(fields_frame, text="开始时间 *", font=('Microsoft YaHei UI', 10)).grid(row=3, column=0, sticky='e', pady=6, padx=4)
        start_e = ttk.Entry(fields_frame, width=32, font=('Microsoft YaHei UI', 10))
        start_e.grid(row=3, column=1, pady=6)
        start_e.insert(0, f"{st_h:02d}:{st_m:02d}")
        entries['start_time_str'] = start_e

        tk.Label(fields_frame, text="结束时间 *", font=('Microsoft YaHei UI', 10)).grid(row=4, column=0, sticky='e', pady=6, padx=4)
        end_e = ttk.Entry(fields_frame, width=32, font=('Microsoft YaHei UI', 10))
        end_e.grid(row=4, column=1, pady=6)
        end_e.insert(0, f"{et_h:02d}:{et_m:02d}")
        entries['end_time_str'] = end_e

        tk.Label(fields_frame, text="实验目的 *", font=('Microsoft YaHei UI', 10)).grid(row=5, column=0, sticky='ne', pady=6, padx=4)
        purpose_text = tk.Text(fields_frame, width=32, height=6, font=('Microsoft YaHei UI', 10))
        purpose_text.grid(row=5, column=1, pady=6)
        if not is_new:
            purpose_text.insert('1.0', safe_get(booking, 'purpose', default=''))
        entries['purpose'] = purpose_text

        if not is_new:
            reason = safe_get(booking, 'reject_reason')
            if reason:
                warn = tk.LabelFrame(fields_frame, text=" ⚠️ 上次驳回原因 ", padx=8, pady=6,
                                     fg='#d9534f', font=('Microsoft YaHei UI', 9, 'bold'))
                warn.grid(row=6, column=0, columnspan=3, sticky='we', pady=8, padx=2)
                tk.Label(warn, text=reason, fg='#d9534f', font=('Microsoft YaHei UI', 9),
                         wraplength=400, justify='left').pack(anchor='w')

        result_var = tk.StringVar(value='')
        result_label = tk.Label(fields_frame, textvariable=result_var, font=('Microsoft YaHei UI', 9), wraplength=350)
        result_label.grid(row=7, column=0, columnspan=3, pady=4)

        def check_conflict():
            try:
                d = datetime.strptime(entries['date'].get().strip(), '%Y-%m-%d').date()
                sh, sm = map(int, entries['start_time_str'].get().strip().split(':'))
                eh, em = map(int, entries['end_time_str'].get().strip().split(':'))
                start_dt = datetime.combine(d, dt_time(sh, sm))
                end_dt = datetime.combine(d, dt_time(eh, em))
                cid = cage.id if (is_new and cage) else safe_get(booking, 'cage', 'id')
                excl = None if is_new else booking.id

                is_valid, _, msg = ConflictService.validate_booking(cid, start_dt, end_dt, excl)
                result_var.set(("✅ " if is_valid else "❌ ") + msg)
                result_label.config(fg='#5cb85c' if is_valid else '#d9534f')
                return is_valid
            except Exception as e:
                result_var.set(f"❌ 输入格式错误：{str(e)}")
                result_label.config(fg='#d9534f')
                return False

        tk.Button(fields_frame, text="🔍 检测时段冲突", command=check_conflict).grid(
            row=8, column=0, columnspan=3, pady=4)

        def save():
            try:
                project = entries['project_name'].get().strip()
                count = int(entries['animal_count'].get())
                purpose = entries['purpose'].get('1.0', tk.END).strip()

                if not all([project, purpose]):
                    messagebox.showwarning("提示", "请填写项目名称和实验目的", parent=dlg)
                    return

                if not check_conflict():
                    if not messagebox.askyesno("冲突提醒", "时段存在冲突，是否仍继续保存？（保存会失败）", parent=dlg):
                        return

                d = datetime.strptime(entries['date'].get().strip(), '%Y-%m-%d').date()
                sh, sm = map(int, entries['start_time_str'].get().strip().split(':'))
                eh, em = map(int, entries['end_time_str'].get().strip().split(':'))
                start_dt = datetime.combine(d, dt_time(sh, sm))
                end_dt = datetime.combine(d, dt_time(eh, em))

                if is_new:
                    success, msg, new_b = BookingService.create_booking(
                        cage_id=cage.id, researcher_id=self.current_user.id,
                        project_name=project, animal_count=count,
                        start_time=start_dt, end_time=end_dt, purpose=purpose)
                    if success:
                        messagebox.showinfo("成功", f"{msg}\n\n预约编号：#{new_b.id}\n状态：草稿\n\n可在『我的预约』提交审批", parent=dlg)
                        dlg.destroy()
                        self._safe_refresh(self._refresh_cage_tab)
                        self._safe_refresh(self._refresh_booking_tab)
                    else:
                        messagebox.showerror("失败", msg, parent=dlg)
                else:
                    success, msg = BookingService.update_booking(
                        booking.id, project_name=project, animal_count=count,
                        start_time=start_dt, end_time=end_dt, purpose=purpose)
                    if success:
                        messagebox.showinfo("成功", f"{msg}\n\n请检查无误后重新提交审批", parent=dlg)
                        dlg.destroy()
                        self._safe_refresh(self._refresh_booking_tab)
                    else:
                        messagebox.showerror("失败", msg, parent=dlg)
            except ValueError as e:
                messagebox.showerror("输入错误", f"数值格式错误：{str(e)}", parent=dlg)
            except Exception as e:
                messagebox.showerror("错误", f"操作失败：{str(e)}", parent=dlg)

        btn_row = tk.Frame(form)
        btn_row.pack(pady=12)
        tk.Button(btn_row, text="💾 保存", bg='#67c23a', fg='white', width=12,
                  relief='flat', font=('Microsoft YaHei UI', 10, 'bold'), command=save).pack(side='left', padx=10)
        tk.Button(btn_row, text="取消", width=12, relief='flat',
                  font=('Microsoft YaHei UI', 10), command=dlg.destroy).pack(side='left', padx=10)

    def _submit_current_booking(self):
        if not self._current_booking_id:
            return
        if messagebox.askyesno("确认提交", f"确定要将预约 #{self._current_booking_id} 提交审批吗？\n\n审批流程：\n① 导师审批\n② 动物房管理员审批\n③ 伦理委员审批"):
            success, msg = BookingService.submit_booking(self._current_booking_id)
            if success:
                messagebox.showinfo("成功", msg)
                self._safe_refresh(self._refresh_booking_tab)
            else:
                messagebox.showerror("失败", msg)

    def _cancel_current_booking(self):
        if not self._current_booking_id:
            return
        if messagebox.askyesno("确认取消", f"确定要取消预约 #{self._current_booking_id} 吗？\n\n取消后时段将释放，其他申请人可预约该时段。"):
            success, msg = BookingService.cancel_booking(self._current_booking_id)
            if success:
                messagebox.showinfo("成功", msg)
                self._safe_refresh(self._refresh_booking_tab)
                self._safe_refresh(self._refresh_cage_tab)
            else:
                messagebox.showerror("失败", msg)

    def _view_approval_history(self):
        if not self._current_booking_id:
            return
        try:
            approvals = ApprovalService.get_approval_history(self._current_booking_id)
        except Exception as e:
            messagebox.showerror("错误", f"加载审批记录失败：{str(e)}")
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"审批记录 - 预约 #{self._current_booking_id}")
        dlg.geometry("520x480")
        dlg.transient(self)

        tk.Label(dlg, text=f"📜 预约 #{self._current_booking_id} - 审批流程记录",
                 font=('Microsoft YaHei UI', 12, 'bold')).pack(pady=12)

        text_frame = tk.Frame(dlg, padx=15)
        text_frame.pack(fill='both', expand=True)

        text = tk.Text(text_frame, font=('Microsoft YaHei UI', 10), wrap='word',
                       relief='solid', borderwidth=1, bg='#fff')
        scroll = ttk.Scrollbar(text_frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        text.tag_config('ok', foreground='#5cb85c')
        text.tag_config('no', foreground='#d9534f')
        text.tag_config('wait', foreground='#f0ad4e')
        text.tag_config('title', font=('Microsoft YaHei UI', 10, 'bold'))

        node_names = {'advisor': '👨‍🏫 导师审批',
                     'facility_manager': '🏢 管理员审批',
                     'ethics_committee': '⚖️  伦理审批'}
        status_names = {'pending': ('待处理', 'wait'),
                       'approved': ('✅ 审批通过', 'ok'),
                       'rejected': ('❌ 已驳回', 'no')}

        for i, approval in enumerate(approvals, 1):
            node_val = safe_get(approval, 'node')
            try: node_val = node_val.value
            except Exception: pass
            node = node_names.get(str(node_val), str(node_val))

            st = safe_get(approval, 'status')
            try: st_val = st.value
            except Exception: st_val = str(st)
            status_text, tag = status_names.get(st_val, (str(st), ''))

            aname = safe_get(approval, 'approver', 'name', default='-')
            updated = safe_get(approval, 'updated_at')
            if isinstance(updated, datetime): updated = updated.strftime('%Y-%m-%d %H:%M:%S')

            comments = safe_get(approval, 'comments', default='（无意见）')

            text.insert(tk.END, f"【第 {i} 级】 {node}\n", 'title')
            text.insert(tk.END, f"  结  果：", '')
            text.insert(tk.END, f"{status_text}\n", tag)
            text.insert(tk.END, f"  审批人：{aname}\n")
            text.insert(tk.END, f"  时  间：{updated}\n")
            text.insert(tk.END, f"  意  见：{comments}\n\n")

        text.config(state='disabled')

        tk.Button(dlg, text="关闭", width=14, command=dlg.destroy,
                  font=('Microsoft YaHei UI', 10)).pack(pady=12)

    # ==================== 审批管理模块 ====================
    def _build_approval_tab(self):
        frame = self.approval_tab
        for widget in frame.winfo_children():
            widget.destroy()

        role_name = UserService.get_role_name(self.current_user.role)
        tk.Label(frame, text=f"🔐 审批工作台 · 当前身份：{role_name}",
                 font=('Microsoft YaHei UI', 12, 'bold'), fg='#2c3e50').pack(anchor='w', padx=10, pady=8)

        nb = ttk.Notebook(frame)
        nb.pack(fill='both', expand=True, padx=8, pady=4)

        pending_frame = tk.Frame(nb)
        nb.add(pending_frame, text='  ⏳ 待我审批  ')

        history_frame = tk.Frame(nb)
        nb.add(history_frame, text='  📜 我审批过的  ')

        self._build_pending_approvals(pending_frame)
        self._build_history_approvals(history_frame)

        nb.bind('<<NotebookTabChanged>>', lambda e: self._safe_refresh(self._refresh_approval_tab))

    def _build_pending_approvals(self, parent):
        top = tk.Frame(parent)
        top.pack(fill='x', padx=6, pady=6)
        tk.Label(top, text="点击下方列表查看详情后可进行审批操作",
                 fg='#868e96', font=('Microsoft YaHei UI', 9)).pack(side='left')
        tk.Button(top, text="🔄 刷新", command=lambda: self._safe_refresh(self._refresh_approval_tab)).pack(side='right')

        columns = ('id', 'project', 'applicant', 'cage', 'time', 'submit', 'node')
        self.pending_tree = ttk.Treeview(parent, columns=columns, show='headings', height=10)
        for col, w in [('id', 60), ('project', 240), ('applicant', 80), ('cage', 120),
                       ('time', 260), ('submit', 120), ('node', 110)]:
            self.pending_tree.column(col, width=w, anchor='w' if col in ['project', 'time'] else 'center')
        for col, t in [('id', '预约ID'), ('project', '项目名称'), ('applicant', '申请人'),
                       ('cage', '笼位'), ('time', '时段'), ('submit', '提交时间'), ('node', '待审批节点')]:
            self.pending_tree.heading(col, text=t)

        pscroll = ttk.Scrollbar(parent, orient='vertical', command=self.pending_tree.yview)
        self.pending_tree.configure(yscrollcommand=pscroll.set)
        pc = tk.Frame(parent)
        pc.pack(fill='both', expand=True, padx=6)
        self.pending_tree.pack(side='left', fill='both', expand=True)
        pscroll.pack(side='right', fill='y')

        bottom = tk.Frame(parent, padx=6, pady=8)
        bottom.pack(fill='x')

        detail_container = tk.Frame(bottom)
        detail_container.pack(side='left', fill='both', expand=True, padx=(0, 10))
        tk.Label(detail_container, text="申请详情：", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w')
        self.pending_detail = tk.Text(detail_container, height=6, font=('Microsoft YaHei UI', 9),
                                      relief='solid', borderwidth=1, bg='#f8f9fa')
        self.pending_detail.pack(fill='x', pady=4)
        self.pending_detail.config(state='disabled')

        btn_col = tk.Frame(bottom)
        btn_col.pack(side='right')

        self.approve_btn = tk.Button(btn_col, text="✅ 通过审批", width=14, state='disabled',
                                     bg='#5cb85c', fg='white', relief='flat',
                                     font=('Microsoft YaHei UI', 10, 'bold'), pady=6, command=self._do_approve)
        self.approve_btn.pack(pady=4)

        self.reject_btn = tk.Button(btn_col, text="❌ 驳回申请", width=14, state='disabled',
                                    bg='#d9534f', fg='white', relief='flat',
                                    font=('Microsoft YaHei UI', 10, 'bold'), pady=6, command=self._do_reject)
        self.reject_btn.pack(pady=4)

        self._current_pending_id = None
        self.pending_tree.bind('<<TreeviewSelect>>', lambda e: self._safe_refresh(self._on_pending_select))

    def _build_history_approvals(self, parent):
        top = tk.Frame(parent)
        top.pack(fill='x', padx=6, pady=6)
        tk.Button(top, text="🔄 刷新", command=lambda: self._safe_refresh(self._refresh_approval_tab)).pack(side='right')

        columns = ('id', 'project', 'node', 'result', 'approver', 'time', 'comments', 'current')
        self.history_tree = ttk.Treeview(parent, columns=columns, show='headings', height=14)
        for col, w in [('id', 60), ('project', 220), ('node', 100), ('result', 90),
                       ('approver', 80), ('time', 120), ('comments', 180), ('current', 100)]:
            self.history_tree.column(col, width=w, anchor='w' if col in ['project', 'comments'] else 'center')
        for col, t in [('id', '预约ID'), ('project', '项目名称'), ('node', '节点'), ('result', '我处理的结果'),
                       ('approver', '审批人'), ('time', '处理时间'), ('comments', '意见'), ('current', '预约当前状态')]:
            self.history_tree.heading(col, text=t)

        hscroll = ttk.Scrollbar(parent, orient='vertical', command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=hscroll.set)
        hc = tk.Frame(parent)
        hc.pack(fill='both', expand=True, padx=6)
        self.history_tree.pack(side='left', fill='both', expand=True)
        hscroll.pack(side='right', fill='y')

    def _refresh_approval_tab(self):
        self._safe_refresh(self._refresh_pending_approvals)
        self._safe_refresh(self._refresh_history_approvals)

    def _refresh_pending_approvals(self):
        for item in self.pending_tree.get_children():
            self.pending_tree.delete(item)

        self._current_pending_id = None
        self.approve_btn.config(state='disabled')
        self.reject_btn.config(state='disabled')
        self.pending_detail.config(state='normal')
        self.pending_detail.delete('1.0', tk.END)
        self.pending_detail.insert('1.0', '(暂无待审批任务，或请点击上方列表选择)\n'
                                   '提示：如果您刚登录后切换过角色账号，请点击刷新按钮')
        self.pending_detail.config(state='disabled')

        try:
            approvals = ApprovalService.get_approvals_for_user(self.current_user.id)
        except Exception as e:
            print(f"加载待审批失败: {e}")
            return

        node_names = {'advisor': '导师', 'facility_manager': '管理员', 'ethics_committee': '伦理'}

        for approval in approvals:
            try:
                booking = safe_get(approval, 'booking')
                if not booking:
                    continue

                st = safe_get(booking, 'start_time')
                et = safe_get(booking, 'end_time')
                if isinstance(st, datetime): st = st.strftime('%Y-%m-%d %H:%M')
                if isinstance(et, datetime): et = et.strftime('%Y-%m-%d %H:%M')

                created = safe_get(booking, 'created_at')
                if isinstance(created, datetime): created = created.strftime('%Y-%m-%d %H:%M')

                cage_code = safe_get(booking, 'cage', 'cage_code', default='-')
                rname = safe_get(booking, 'researcher', 'name', default='-')

                node_val = safe_get(approval, 'node')
                try: node_val = node_val.value
                except Exception: pass
                node_disp = node_names.get(str(node_val), str(node_val))

                self.pending_tree.insert('', tk.END, iid=str(safe_get(booking, 'id')),
                    values=(
                        safe_get(booking, 'id', default=''),
                        safe_get(booking, 'project_name', default=''),
                        rname,
                        cage_code,
                        f"{st}\n{et}",
                        created,
                        node_disp + '审批'
                    ))
            except Exception as e:
                print(f"渲染待审批项失败: {e}")
                continue

    def _refresh_history_approvals(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            from db.database import SessionLocal
            from models.approval import Approval, ApprovalStatus
            from sqlalchemy.orm import joinedload
            db = SessionLocal()
            try:
                approvals = db.query(Approval).options(
                    joinedload(Approval.booking).joinedload('cage'),
                    joinedload(Approval.booking).joinedload('researcher'),
                    joinedload(Approval.approver)
                ).filter(
                    Approval.approver_id == self.current_user.id,
                    Approval.status != ApprovalStatus.PENDING
                ).order_by(Approval.updated_at.desc()).all()

                for a in approvals:
                    _ = safe_get(a, 'booking', 'cage', 'cage_code')
                    _ = safe_get(a, 'booking', 'researcher', 'name')
            finally:
                db.close()
        except Exception as e:
            print(f"加载历史审批失败: {e}")
            return

        node_names = {'advisor': '导师', 'facility_manager': '管理员', 'ethics_committee': '伦理'}
        status_map = {'approved': ('✅ 通过', '#5cb85c'), ('rejected': ('❌ 驳回', '#d9534f')}

        for approval in approvals:
            try:
                booking = safe_get(approval, 'booking')
                st_val = safe_get(approval, 'status')
                try: st_val = st_val.value
                except Exception: pass

                status_text, _ = status_map.get(str(st_val), (str(st_val), ''))
                node_val = safe_get(approval, 'node')
                try: node_val = node_val.value
                except Exception: pass

                updated = safe_get(approval, 'updated_at')
                if isinstance(updated, datetime): updated = updated.strftime('%Y-%m-%d %H:%M')

                self.history_tree.insert('', tk.END,
                    values=(
                        safe_get(booking, 'id', default=''),
                        safe_get(booking, 'project_name', default=''),
                        node_names.get(str(node_val), str(node_val)),
                        status_text,
                        safe_get(approval, 'approver', 'name', default=''),
                        updated,
                        safe_get(approval, 'comments', default='-'),
                        BookingService.get_booking_status_text(safe_get(booking, 'status')) if booking else '-'
                    ))
            except Exception as e:
                print(f"渲染历史项失败: {e}")
                continue

    def _on_pending_select(self):
        selection = self.pending_tree.selection()
        can_act = False
        detail_text = '(请点击上方列表选择一条待审批记录)'
        self._current_pending_id = None

        if selection:
            try:
                booking_id = int(selection[0])
                booking = BookingService.get_booking_by_id(booking_id)
                if booking:
                    self._current_pending_id = booking_id

                    st = safe_get(booking, 'start_time')
                    et = safe_get(booking, 'end_time')
                    if isinstance(st, datetime): st = st.strftime('%Y-%m-%d %H:%M')
                    if isinstance(et, datetime): et = et.strftime('%Y-%m-%d %H:%M')

                    cage_code = safe_get(booking, 'cage', 'cage_code', default='-')
                    cage_room = safe_get(booking, 'cage', 'room', default='')
                    atype = safe_get(booking, 'cage', 'animal_type', default='')
                    rname = safe_get(booking, 'researcher', 'name', default='')

                    detail_text = (
                        f"📋 预约 #{booking.id} - {safe_get(booking, 'project_name', default='')}\n"
                        f"👤 申请人：{rname}\n"
                        f"🏠 笼位：{cage_code} - {cage_room}（{atype}）\n"
                        f"🔢 数量：{safe_get(booking, 'animal_count', default='')} 只\n"
                        f"⏰ 时段：{st} 至 {et}\n"
                        f"📄 目的：{safe_get(booking, 'purpose', default='')}"
                    )

                    rej = safe_get(booking, 'reject_reason')
                    if rej:
                        detail_text += f"\n\n⚠️ 上一步驳回原因：{rej}"

                    can_act = True
            except Exception as e:
                detail_text = f"加载详情失败：{str(e)}"

        self.pending_detail.config(state='normal')
        self.pending_detail.delete('1.0', tk.END)
        self.pending_detail.insert('1.0', detail_text)
        self.pending_detail.config(state='disabled')

        self.approve_btn.config(state='normal' if can_act else 'disabled')
        self.reject_btn.config(state='normal' if can_act else 'disabled')

    def _do_approve(self):
        if not self._current_pending_id:
            return
        comments = simpledialog.askstring("审批意见", "请输入审批意见（可选）：",
                                          parent=self, initialvalue="同意，符合要求。")
        if comments is None:
            return
        success, msg = ApprovalService.approve(self._current_pending_id, self.current_user.id, comments)
        if success:
            messagebox.showinfo("✅ 审批通过", msg)
            self._safe_refresh(self._refresh_approval_tab)
            self._safe_refresh(self._refresh_booking_tab)
            self._safe_refresh(self._refresh_access_tab)
        else:
            messagebox.showerror("失败", msg)

    def _do_reject(self):
        if not self._current_pending_id:
            return

        dlg = tk.Toplevel(self)
        dlg.title("驳回申请")
        dlg.geometry("460x280")
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg, text=f"驳回预约 #{self._current_pending_id}",
                 font=('Microsoft YaHei UI', 12, 'bold'), fg='#d9534f').pack(pady=12)

        tk.Label(dlg, text="❗ 请详细填写驳回原因（必填）：",
                 font=('Microsoft YaHei UI', 10)).pack(padx=20, anchor='w')

        text = tk.Text(dlg, height=6, font=('Microsoft YaHei UI', 10))
        text.pack(padx=20, pady=8, fill='x')

        def confirm():
            reason = text.get('1.0', tk.END).strip()
            if not reason:
                messagebox.showwarning("提示", "驳回原因必填，请填写后再提交", parent=dlg)
                return
            success, msg = ApprovalService.reject(self._current_pending_id, self.current_user.id, reason)
            if success:
                messagebox.showinfo("已驳回", msg, parent=dlg)
                dlg.destroy()
                self._safe_refresh(self._refresh_approval_tab)
                self._safe_refresh(self._refresh_booking_tab)
            else:
                messagebox.showerror("失败", msg, parent=dlg)

        row = tk.Frame(dlg)
        row.pack(pady=10)
        tk.Button(row, text="确认驳回", bg='#d9534f', fg='white', width=12,
                  relief='flat', font=('Microsoft YaHei UI', 10, 'bold'), command=confirm).pack(side='left', padx=8)
        tk.Button(row, text="取消", width=12, relief='flat',
                  font=('Microsoft YaHei UI', 10), command=dlg.destroy).pack(side='left', padx=8)

    # ==================== 准入登记模块 ====================
    def _build_access_tab(self):
        frame = self.access_tab
        for widget in frame.winfo_children():
            widget.destroy()

        is_manager = self.current_user.role == UserRole.FACILITY_MANAGER

        if is_manager:
            entry_box = tk.LabelFrame(frame, text=" ⚡ 快速进出登记 ", padx=12, pady=10,
                                     font=('Microsoft YaHei UI', 10, 'bold'))
            entry_box.pack(fill='x', padx=10, pady=8)

            row = tk.Frame(entry_box)
            row.pack(fill='x')

            tk.Label(row, text="扫描/输入准入码：", font=('Microsoft YaHei UI', 10)).pack(side='left', padx=4)
            self.access_code_entry = ttk.Entry(row, font=('Microsoft YaHei UI', 12), width=26)
            self.access_code_entry.pack(side='left', padx=6)

            tk.Button(row, text="🚪 登记进入", bg='#5cb85c', fg='white', relief='flat',
                      font=('Microsoft YaHei UI', 10, 'bold'), padx=14, pady=5,
                      command=self._do_record_entry).pack(side='left', padx=6)
            tk.Button(row, text="🚪 登记离开", bg='#f0ad4e', fg='white', relief='flat',
                      font=('Microsoft YaHei UI', 10, 'bold'), padx=14, pady=5,
                      command=self._do_record_exit).pack(side='left', padx=6)

        nb = ttk.Notebook(frame)
        nb.pack(fill='both', expand=True, padx=8, pady=4)

        pending_frame = tk.Frame(nb)
        nb.add(pending_frame, text='  ✅ 待准入（已审批通过）  ')

        active_frame = tk.Frame(nb)
        nb.add(active_frame, text='  ⏰ 场内（进行中）  ')

        history_frame = tk.Frame(nb)
        nb.add(history_frame, text='  📜 进出记录  ')

        self._build_pending_access(pending_frame, is_manager)
        self._build_active_access(active_frame, is_manager)
        self._build_history_access(history_frame)

        nb.bind('<<NotebookTabChanged>>', lambda e: self._safe_refresh(self._refresh_access_tab))

    def _build_pending_access(self, parent, is_manager):
        top = tk.Frame(parent)
        top.pack(fill='x', padx=6, pady=6)
        if is_manager:
            tk.Label(top, text="💡 双击列表可生成准入码", fg='#868e96', font=('Microsoft YaHei UI', 9)).pack(side='left')
        tk.Button(top, text="🔄 刷新", command=lambda: self._safe_refresh(self._refresh_access_tab)).pack(side='right')

        columns = ('id', 'project', 'applicant', 'cage', 'time', 'status', 'action', 'code')
        self.pending_access_tree = ttk.Treeview(parent, columns=columns, show='headings', height=12)
        widths = [('id', 70), ('project', 230), ('applicant', 80), ('cage', 140),
                  ('time', 250), ('status', 90), ('action', 100), ('code', 150)]
        for c, w in widths:
            anchor = 'w' if c in ['project', 'time'] else 'center'
            self.pending_access_tree.column(c, width=w, anchor=anchor)
        titles = [('id', '预约ID'), ('project', '项目'), ('applicant', '申请人'),
                  ('cage', '笼位'), ('time', '时段'), ('status', '状态'), ('action', '操作'), ('code', '准入码')]
        for c, t in titles: self.pending_access_tree.heading(c, text=t)

        ps = ttk.Scrollbar(parent, orient='vertical', command=self.pending_access_tree.yview)
        self.pending_access_tree.configure(yscrollcommand=ps.set)
        pfc = tk.Frame(parent)
        pfc.pack(fill='both', expand=True, padx=6)
        self.pending_access_tree.pack(side='left', fill='both', expand=True)
        ps.pack(side='right', fill='y')

        if is_manager:
            self.pending_access_tree.bind('<Double-1>', self._on_pending_access_dclick)

    def _build_active_access(self, parent, is_manager):
        top = tk.Frame(parent)
        top.pack(fill='x', padx=6, pady=6)

        self.active_count_label = tk.Label(top, text="当前场内：0 人",
                                            font=('Microsoft YaHei UI', 11, 'bold'), fg='#f0ad4e')
        self.active_count_label.pack(side='left')
        if is_manager:
            tk.Label(top, text="  (双击进行中记录可登记离开)",
                     fg='#868e96', font=('Microsoft YaHei UI', 9)).pack(side='left', padx=8)
        tk.Button(top, text="🔄 刷新", command=lambda: self._safe_refresh(self._refresh_access_tab)).pack(side='right')

        columns = ('code', 'booking_id', 'applicant', 'cage', 'entry', 'registrar', 'action')
        self.active_access_tree = ttk.Treeview(parent, columns=columns, show='headings', height=12)
        widths = [('code', 150), ('booking_id', 70), ('applicant', 80), ('cage', 120),
                  ('entry', 150), ('registrar', 80), ('action', 120)]
        for c, w in widths:
            self.active_access_tree.column(c, width=w, anchor='center' if c != 'code' else 'w')
        titles = [('code', '准入码'), ('booking_id', '预约ID'), ('applicant', '申请人'),
                  ('cage', '笼位'), ('entry', '进入时间'), ('registrar', '登记人'), ('action', '操作')]
        for c, t in titles: self.active_access_tree.heading(c, text=t)

        acs = ttk.Scrollbar(parent, orient='vertical', command=self.active_access_tree.yview)
        self.active_access_tree.configure(yscrollcommand=acs.set)
        afc = tk.Frame(parent)
        afc.pack(fill='both', expand=True, padx=6)
        self.active_access_tree.pack(side='left', fill='both', expand=True)
        acs.pack(side='right', fill='y')

        if is_manager:
            self.active_access_tree.bind('<Double-1>', self._on_active_access_dclick)

    def _build_history_access(self, parent):
        top = tk.Frame(parent)
        top.pack(fill='x', padx=6, pady=6)
        tk.Button(top, text="🔄 刷新", command=lambda: self._safe_refresh(self._refresh_access_tab)).pack(side='right')

        columns = ('code', 'booking_id', 'applicant', 'cage', 'entry', 'exit', 'duration', 'registrar')
        self.history_access_tree = ttk.Treeview(parent, columns=columns, show='headings', height=14)
        widths = [('code', 150), ('booking_id', 70), ('applicant', 80), ('cage', 120),
                  ('entry', 150), ('exit', 150), ('duration', 80), ('registrar', 80)]
        for c, w in widths:
            self.history_access_tree.column(c, width=w, anchor='center' if c != 'code' else 'w')
        titles = [('code', '准入码'), ('booking_id', '预约ID'), ('applicant', '申请人'),
                  ('cage', '笼位'), ('entry', '进入时间'), ('exit', '离开时间'),
                  ('duration', '时长(h)'), ('registrar', '登记人')]
        for c, t in titles: self.history_access_tree.heading(c, text=t)

        hcs = ttk.Scrollbar(parent, orient='vertical', command=self.history_access_tree.yview)
        self.history_access_tree.configure(yscrollcommand=hcs.set)
        hfc = tk.Frame(parent)
        hfc.pack(fill='both', expand=True, padx=6)
        self.history_access_tree.pack(side='left', fill='both', expand=True)
        hcs.pack(side='right', fill='y')

    def _refresh_access_tab(self):
        self._safe_refresh(self._refresh_pending_access)
        self._safe_refresh(self._refresh_active_access)
        self._safe_refresh(self._refresh_history_access)

    def _refresh_pending_access(self):
        for item in self.pending_access_tree.get_children():
            self.pending_access_tree.delete(item)

        try:
            bookings = BookingService.get_bookings_by_status(BookingStatus.APPROVED)
        except Exception:
            return

        is_manager = self.current_user.role == UserRole.FACILITY_MANAGER

        for booking in bookings:
            try:
                access = AccessService.get_access_by_booking(safe_get(booking, 'id', default=0))
                if access and safe_get(access, 'is_active'):
                    continue

                st = safe_get(booking, 'start_time')
                et = safe_get(booking, 'end_time')
                if isinstance(st, datetime): st = st.strftime('%Y-%m-%d %H:%M')
                if isinstance(et, datetime): et = et.strftime('%Y-%m-%d %H:%M')

                cage_code = safe_get(booking, 'cage', 'cage_code', default='-')
                cage_room = safe_get(booking, 'cage', 'room', default='')
                rname = safe_get(booking, 'researcher', 'name', default='-')

                acc_code = safe_get(access, 'access_code', default='未生成') if access else '未生成'
                action = "🖱️双击生成" if is_manager else "-"

                self.pending_access_tree.insert('', tk.END, iid=str(safe_get(booking, 'id')),
                    values=(
                        safe_get(booking, 'id'),
                        safe_get(booking, 'project_name', default=''),
                        rname,
                        f"{cage_code} ({cage_room})",
                        f"{st}\n{et}",
                        BookingService.get_booking_status_text(safe_get(booking, 'status')),
                        action,
                        acc_code
                    ))
            except Exception as e:
                print(f"渲染待准入失败: {e}")
                continue

    def _refresh_active_access(self):
        for item in self.active_access_tree.get_children():
            self.active_access_tree.delete(item)

        try:
            access_list = AccessService.get_active_access_registrations()
        except Exception:
            access_list = []

        is_manager = self.current_user.role == UserRole.FACILITY_MANAGER
        count = 0

        for access in access_list:
            try:
                booking = safe_get(access, 'booking')
                if not booking:
                    continue
                count += 1

                entry = safe_get(access, 'entry_time')
                if isinstance(entry, datetime): entry = entry.strftime('%Y-%m-%d %H:%M')
                elif entry is None: entry = '(待进入)'

                cage_code = safe_get(booking, 'cage', 'cage_code', default='-')
                rname = safe_get(booking, 'researcher', 'name', default='-')
                acc = safe_get(access, 'access_code', default='')

                has_entered = safe_get(access, 'entry_time') is not None
                has_exited = safe_get(access, 'exit_time') is not None
                action = "🖱️双击登记离开" if (is_manager and has_entered and not has_exited) else "等待进入"

                self.active_access_tree.insert('', tk.END, iid=acc,
                    values=(acc, safe_get(booking, 'id'), rname, cage_code, entry,
                           safe_get(access, 'registered_by', default=''), action))
            except Exception as e:
                print(f"渲染进行中失败: {e}")
                continue

        self.active_count_label.config(text=f"当前场内人员：{count} 人")

    def _refresh_history_access(self):
        for item in self.history_access_tree.get_children():
            self.history_access_tree.delete(item)

        try:
            access_list = AccessService.get_all_access_registrations()
        except Exception:
            return

        for access in access_list:
            try:
                booking = safe_get(access, 'booking')
                if not booking:
                    continue
                if safe_get(access, 'is_active') and not safe_get(access, 'exit_time'):
                    continue

                entry = safe_get(access, 'entry_time')
                exit_ = safe_get(access, 'exit_time')
                if isinstance(entry, datetime): entry = entry.strftime('%Y-%m-%d %H:%M')
                elif entry is None: entry = '-'
                if isinstance(exit_, datetime): exit_ = exit_.strftime('%Y-%m-%d %H:%M')
                elif exit_ is None: exit_ = '-'

                duration = '-'
                et_obj = safe_get(access, 'entry_time')
                ex_obj = safe_get(access, 'exit_time')
                if isinstance(et_obj, datetime) and isinstance(ex_obj, datetime):
                    hrs = (ex_obj - et_obj).total_seconds() / 3600
                    duration = f"{hrs:.1f}"

                cage_code = safe_get(booking, 'cage', 'cage_code', default='-')
                rname = safe_get(booking, 'researcher', 'name', default='-')

                self.history_access_tree.insert('', tk.END,
                    values=(safe_get(access, 'access_code'), safe_get(booking, 'id'),
                           rname, cage_code, entry, exit_, duration,
                           safe_get(access, 'registered_by', default='')))
            except Exception as e:
                print(f"渲染历史失败: {e}")
                continue

    def _on_pending_access_dclick(self, event):
        if self.current_user.role != UserRole.FACILITY_MANAGER:
            return
        item = self.pending_access_tree.identify('item', event.x, event.y)
        if not item:
            return
        try:
            booking_id = int(item)
        except Exception:
            return
        if not messagebox.askyesno("确认", f"确定要为预约 #{booking_id} 生成准入码吗？"):
            return
        try:
            success, msg, access = AccessService.create_access_registration(booking_id, self.current_user.name)
            if success and access:
                self._show_access_code_dialog(safe_get(access, 'access_code', default=''),
                                            BookingService.get_booking_by_id(booking_id))
                self._safe_refresh(self._refresh_pending_access)
                self._safe_refresh(self._refresh_active_access)
            else:
                messagebox.showerror("失败", msg)
        except Exception as e:
            messagebox.showerror("错误", f"生成失败：{str(e)}")

    def _on_active_access_dclick(self, event):
        if self.current_user.role != UserRole.FACILITY_MANAGER:
            return
        item = self.active_access_tree.identify('item', event.x, event.y)
        if not item:
            return
        item_vals = self.active_access_tree.item(item)['values']
        if not item_vals or len(item_vals) < 7:
            return
        action = str(item_vals[6])
        if '离开' not in action:
            messagebox.showinfo("提示", "该记录尚未进入或已离开")
            return
        code = str(item_vals[0])
        if not messagebox.askyesno("确认", f"确定登记准入码 {code} 离开吗？"):
            return
        success, msg = AccessService.record_exit(code)
        if success:
            messagebox.showinfo("成功", msg)
            self._safe_refresh(self._refresh_access_tab)
            self._safe_refresh(self._refresh_booking_tab)
        else:
            messagebox.showerror("失败", msg)

    def _do_record_entry(self):
        code = self.access_code_entry.get().strip()
        if not code:
            messagebox.showwarning("提示", "请先输入或扫描准入码")
            return
        success, msg = AccessService.record_entry(code)
        if success:
            messagebox.showinfo("✅ 进入成功", msg)
            self.access_code_entry.delete(0, tk.END)
            self._safe_refresh(self._refresh_access_tab)
        else:
            messagebox.showwarning("⚠️ 进入失败", msg)

    def _do_record_exit(self):
        code = self.access_code_entry.get().strip()
        if not code:
            messagebox.showwarning("提示", "请先输入或扫描准入码")
            return
        success, msg = AccessService.record_exit(code)
        if success:
            messagebox.showinfo("✅ 离开成功", msg)
            self.access_code_entry.delete(0, tk.END)
            self._safe_refresh(self._refresh_access_tab)
            self._safe_refresh(self._refresh_booking_tab)
        else:
            messagebox.showwarning("⚠️ 离开失败", msg)

    def _show_access_code_dialog(self, code, booking):
        dlg = tk.Toplevel(self)
        dlg.title("准入码生成成功")
        dlg.geometry("440x360")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg='#f8f9fa')

        tk.Label(dlg, text="✅ 准入码已生成", bg='#f8f9fa',
                 font=('Microsoft YaHei UI', 14, 'bold'), fg='#5cb85c').pack(pady=(20, 10))

        code_frame = tk.Frame(dlg, bg='white', highlightbackground='#409eff', highlightthickness=2)
        code_frame.pack(padx=40, pady=10)
        tk.Label(code_frame, text=code, font=('Consolas', 24, 'bold'),
                 fg='#409eff', bg='white', padx=20, pady=12).pack()

        if booking:
            info_frame = tk.LabelFrame(dlg, text=" 预约信息 ", padx=12, pady=8,
                                      font=('Microsoft YaHei UI', 9), bg='#f8f9fa')
            info_frame.pack(padx=30, pady=10, fill='x')

            st = safe_get(booking, 'start_time')
            et = safe_get(booking, 'end_time')
            if isinstance(st, datetime): st = st.strftime('%Y-%m-%d %H:%M')
            if isinstance(et, datetime): et = et.strftime('%Y-%m-%d %H:%M')

            info_lines = [
                f"预约编号：#{safe_get(booking, 'id')}",
                f"项目名称：{safe_get(booking, 'project_name', default='')}",
                f"笼位：{safe_get(booking, 'cage', 'cage_code', default='-')}",
                f"时段：{st} 至 {et}"
            ]
            for line in info_lines:
                tk.Label(info_frame, text=line, bg='#f8f9fa',
                         font=('Microsoft YaHei UI', 10), anchor='w').pack(anchor='w', pady=1)

        tk.Label(dlg, text="📋 请将此准入码告知申请人，进入时核验使用",
                 bg='#f8f9fa', fg='#868e96', font=('Microsoft YaHei UI', 9),
                 wraplength=360).pack(pady=5)

        tk.Button(dlg, text="知道了", bg='#409eff', fg='white',
                  width=14, relief='flat', font=('Microsoft YaHei UI', 10, 'bold'),
                  padx=10, pady=6, command=dlg.destroy).pack(pady=12)


if __name__ == '__main__':
    try:
        app = AnimalLabApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("严重错误", f"程序运行异常：{str(e)}\n\n{traceback.format_exc()}")
        sys.exit(1)
