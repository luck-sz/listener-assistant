from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from typing import Literal, cast

SignalRow = tuple[str, str, str, str, str, str, str]

INITIAL_SIGNALS: list[SignalRow] = [
    ("600519", "贵州茅台", "1745.00", "+1.25%", "MACD金叉买入", "buy", "14:32:05"),
    ("000858", "五粮液", "138.50", "+0.82%", "底背离买入", "buy", "14:15:42"),
    ("300750", "宁德时代", "192.15", "-2.45%", "MACD死叉卖出", "sell", "13:58:11"),
    ("601318", "中国平安", "52.30", "-1.12%", "顶背离卖出", "sell", "13:42:00"),
    ("000333", "美的集团", "71.25", "+0.45%", "MACD金叉买入", "buy", "11:20:15"),
]

INITIAL_LOGS = [
    ("14:35:18", "监听服务已连接至本地策略引擎。"),
    ("14:34:50", "沪深自选池完成第 6 轮扫描。"),
    ("14:32:05", "贵州茅台触发 MACD 金叉买入信号。"),
    ("14:15:42", "五粮液触发底背离买入信号。"),
    ("13:58:11", "宁德时代触发 MACD 死叉卖出信号。"),
]

RULES = [
    ("MACD金叉买入", "快慢线金叉且量能同步放大，适合捕捉趋势启动。", "启用中"),
    ("MACD死叉卖出", "短线动能转弱，防止强势股回撤扩大。", "启用中"),
    ("底背离买入", "价格创新低但动能未创新低，用于低位反转确认。", "启用中"),
    ("顶背离卖出", "价格创新高但动能跟不上，用于高位风险控制。", "启用中"),
]

RULE_PERIODS = ("5分钟", "15分钟", "30分钟", "日线")


class AddWatchlistDialog(tk.Toplevel):
    def __init__(self, parent: "StockListenerAssistant") -> None:
        super().__init__(parent.root)
        self.parent = parent
        self.title("Add Stock Listener")
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(bg="#0C0F10")
        self.transient(parent.root)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.code_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.change_var = tk.StringVar()
        self.signal_var = tk.StringVar(value="MACD金叉买入")

        self._build()

    def _build(self) -> None:
        shell = tk.Frame(self, bg="#0C0F10")
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        card = tk.Frame(
            shell,
            bg="#FFFFFF",
            highlightbackground="#E2E8EE",
            highlightthickness=1,
            padx=28,
            pady=28,
        )
        card.pack(fill="both", expand=True)

        top = tk.Frame(card, bg="#FFFFFF")
        top.pack(fill="x")
        tk.Label(
            top,
            text="添加股票监听",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left")
        close_button = tk.Button(
            top,
            text="x",
            command=self.destroy,
            bg="#FFFFFF",
            fg="#737C81",
            activebackground="#F1F4F7",
            activeforeground="#2B3438",
            bd=0,
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            padx=8,
            pady=2,
        )
        close_button.pack(side="right")

        form = tk.Frame(card, bg="#FFFFFF")
        form.pack(fill="both", expand=True, pady=(22, 0))
        form.columnconfigure(0, weight=1)

        tk.Label(
            form,
            text="股票代码",
            bg="#FFFFFF",
            fg="#586065",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        code_wrap = tk.Frame(
            form,
            bg="#EAEEF2",
            highlightbackground="#E2E9EE",
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        code_wrap.pack(fill="x", pady=(10, 0))
        tk.Label(
            code_wrap,
            text="Q",
            bg="#EAEEF2",
            fg="#737C81",
            font=("Segoe UI", 12, "bold"),
            width=2,
        ).pack(side="left")
        code_entry = tk.Entry(
            code_wrap,
            textvariable=self.code_var,
            bg="#EAEEF2",
            fg="#2B3438",
            insertbackground="#1353D8",
            relief="flat",
            font=("Segoe UI", 11),
        )
        code_entry.pack(side="left", fill="x", expand=True)
        code_entry.focus_set()

        tk.Label(
            form,
            text="请输入沪深/港股/美股代码。系统将自动识别市场并加载实时 K 线数据及预警算法。",
            bg="#FFFFFF",
            fg="#7A848D",
            font=("Segoe UI", 9),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(12, 18))

        extra = tk.Frame(form, bg="#FFFFFF")
        extra.pack(fill="x")
        extra.columnconfigure(0, weight=1)
        extra.columnconfigure(1, weight=1)

        self._compact_field(extra, "股票名称", self.name_var, 0, 0)
        self._compact_field(extra, "最新价格", self.price_var, 0, 1)
        self._compact_field(extra, "当日涨幅", self.change_var, 1, 0)

        signal_box = tk.Frame(extra, bg="#FFFFFF")
        signal_box.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(14, 0))
        tk.Label(
            signal_box,
            text="信号类型",
            bg="#FFFFFF",
            fg="#586065",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        ttk.Combobox(
            signal_box,
            textvariable=self.signal_var,
            values=[rule[0] for rule in RULES],
            state="readonly",
        ).pack(fill="x", pady=(8, 0))

        actions = tk.Frame(card, bg="#FFFFFF")
        actions.pack(fill="x", pady=(26, 0))
        cancel = tk.Button(
            actions,
            text="取消",
            command=self.destroy,
            bg="#E2E9EE",
            fg="#586065",
            activebackground="#D7DEE5",
            activeforeground="#2B3438",
            bd=0,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=26,
            pady=12,
        )
        cancel.pack(side="left", fill="x", expand=True, padx=(0, 8))
        confirm = tk.Button(
            actions,
            text="确认添加",
            command=self._submit,
            bg="#1353D8",
            fg="#FFFFFF",
            activebackground="#0B50D5",
            activeforeground="#FFFFFF",
            bd=0,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=26,
            pady=12,
        )
        confirm.pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _field(
        self, parent: tk.Widget, label: str, variable: tk.StringVar, row: int
    ) -> None:
        tk.Label(
            parent,
            text=label,
            bg="#FFFFFF",
            fg="#54606A",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=row, column=0, sticky="w", pady=8)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=8)

    def _compact_field(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
    ) -> None:
        frame = tk.Frame(parent, bg="#FFFFFF")
        frame.grid(
            row=row,
            column=column,
            sticky="ew",
            padx=(0, 12) if column == 0 else (12, 0),
            pady=(0 if row == 0 else 14, 0),
        )
        tk.Label(
            frame,
            text=label,
            bg="#FFFFFF",
            fg="#586065",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        ttk.Entry(frame, textvariable=variable).pack(fill="x", pady=(8, 0))

    def _submit(self) -> None:
        code = self.code_var.get().strip()
        name = self.name_var.get().strip()
        price = self.price_var.get().strip() or "0.00"
        change = self.change_var.get().strip() or "+0.00%"
        signal_name = self.signal_var.get().strip()

        if not code or not name:
            self.parent.show_toast("请至少填写证券代码和证券名称。")
            return

        tone = "sell" if "卖出" in signal_name else "buy"
        timestamp = time.strftime("%H:%M:%S")
        row: SignalRow = (code, name, price, change, signal_name, tone, timestamp)
        self.parent.add_signal(row)
        self.destroy()


class StockListenerAssistant:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Stock Listener Assistant")
        self.root.geometry("1480x920")
        self.root.minsize(1180, 760)
        self.root.configure(bg="#F4F7FB")

        self.signals: list[SignalRow] = list(INITIAL_SIGNALS)
        self.logs: list[tuple[str, str]] = list(INITIAL_LOGS)
        self.active_page = "watchlist"

        self.clock_var = tk.StringVar(value="--:--:--")
        self.status_var = tk.StringVar(value="引擎已启动")
        self.buy_count_var = tk.StringVar(value="0")
        self.sell_count_var = tk.StringVar(value="0")
        self.total_count_var = tk.StringVar(value="0")
        self.toast_var = tk.StringVar(value="")
        self.macd_enabled_var = tk.BooleanVar(value=True)
        self.macd_threshold_var = tk.DoubleVar(value=5.0)
        self.macd_threshold_text_var = tk.StringVar(value="> 5.0")
        self.macd_mode_var = tk.StringVar(value="从下方金叉穿过")
        self.divergence_enabled_var = tk.BooleanVar(value=False)
        self.divergence_limit_var = tk.StringVar(value="")
        self.divergence_period_var = tk.StringVar(value="15分钟")

        self.nav_labels: dict[str, tk.Label] = {}
        self.period_buttons: dict[str, tk.Button] = {}

        self._configure_styles()
        self._build_ui()
        self.refresh_dashboard()
        self._tick_clock()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background="#F4F7FB")
        style.configure(
            "Primary.TButton",
            background="#1353D8",
            foreground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            padding=(18, 12),
            borderwidth=0,
        )
        style.map("Primary.TButton", background=[("active", "#0B50D5")])
        style.configure(
            "Signal.Treeview",
            background="#FFFFFF",
            foreground="#2B3438",
            fieldbackground="#FFFFFF",
            rowheight=44,
            font=("Consolas", 10),
            borderwidth=0,
        )
        style.configure(
            "Signal.Treeview.Heading",
            background="#FFFFFF",
            foreground="#737C81",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            borderwidth=0,
        )
        style.map(
            "Signal.Treeview",
            background=[("selected", "#DBE1FF")],
            foreground=[("selected", "#0B50D5")],
        )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()
        self._build_toast()

    def _build_header(self) -> None:
        header = tk.Frame(
            self.root,
            bg="#F8F9FB",
            height=72,
            highlightbackground="#E8EDF2",
            highlightthickness=1,
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=1)

        left = tk.Frame(header, bg="#F8F9FB")
        left.grid(row=0, column=0, sticky="w", padx=26)
        tk.Label(
            left,
            text="Financial Signal Monitor",
            bg="#F8F9FB",
            fg="#586065",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            left,
            text="股票监听助手",
            bg="#F8F9FB",
            fg="#1353D8",
            font=("Segoe UI", 20, "bold"),
        ).grid(row=1, column=0, sticky="w")

        center = tk.Frame(header, bg="#F8F9FB")
        center.grid(row=0, column=1)
        for idx, item in enumerate(
            (("watchlist", "自选"), ("rules", "规则"), ("logs", "日志"))
        ):
            key, title = item
            label = tk.Label(
                center,
                text=title,
                bg="#F8F9FB",
                fg="#586065",
                font=("Segoe UI", 10, "bold"),
                padx=18,
                pady=4,
                cursor="hand2",
            )
            label.grid(row=0, column=idx)
            label.bind("<Button-1>", lambda _event, page=key: self.switch_page(page))
            self.nav_labels[key] = label

        right = tk.Frame(header, bg="#F8F9FB")
        right.grid(row=0, column=2, sticky="e", padx=26)
        pill = tk.Frame(
            right,
            bg="#F1F4F7",
            padx=16,
            pady=8,
            highlightbackground="#DFE5EA",
            highlightthickness=1,
        )
        pill.grid(row=0, column=0, sticky="e")
        tk.Label(
            pill,
            text="● 运行中",
            bg="#F1F4F7",
            fg="#006D4A",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, padx=(0, 10))
        tk.Label(
            pill,
            text="已连接",
            bg="#F1F4F7",
            fg="#1353D8",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=1, padx=(0, 10))
        tk.Label(
            pill,
            textvariable=self.clock_var,
            bg="#F1F4F7",
            fg="#586065",
            font=("Consolas", 10, "bold"),
        ).grid(row=0, column=2)

    def _build_body(self) -> None:
        body = ttk.Frame(self.root, style="App.TFrame", padding=(24, 24, 24, 16))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        cards = tk.Frame(body, bg="#F4F7FB")
        cards.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        for col in range(4):
            cards.columnconfigure(col, weight=1)

        self._hero_card(cards).grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.buy_metric = self._metric_card(
            cards, "买入信号", self.buy_count_var, "较上一轮 +3", "#006D4A"
        )
        self.buy_metric.grid(row=0, column=1, sticky="nsew", padx=6)
        self.sell_metric = self._metric_card(
            cards, "卖出信号", self.sell_count_var, "风险集中在新能源板块", "#9E3F4E"
        )
        self.sell_metric.grid(row=0, column=2, sticky="nsew", padx=6)
        self.total_metric = self._metric_card(
            cards, "总信号数", self.total_count_var, "桌面端实时轮询", "#586065"
        )
        self.total_metric.grid(row=0, column=3, sticky="nsew", padx=(12, 0))

        self.page_container = tk.Frame(body, bg="#F4F7FB")
        self.page_container.grid(row=1, column=0, sticky="nsew")
        self.page_container.columnconfigure(0, weight=1)
        self.page_container.rowconfigure(0, weight=1)

        self.pages = {
            "watchlist": self._build_watchlist_page(self.page_container),
            "rules": self._build_rules_page(self.page_container),
            "logs": self._build_logs_page(self.page_container),
        }
        for frame in self.pages.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self.fab_button = ttk.Button(
            body, text="添加自选", style="Primary.TButton", command=self.open_add_dialog
        )
        self.fab_button.place(relx=0.985, rely=0.985, anchor="se")

        self.switch_page("watchlist")

    def _hero_card(self, parent: tk.Widget) -> tk.Frame:
        frame = tk.Frame(parent, bg="#1353D8", padx=24, pady=22)
        tk.Label(
            frame,
            text="今日概览",
            bg="#1353D8",
            fg="#C9D7FF",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            textvariable=self.total_count_var,
            bg="#1353D8",
            fg="#FFFFFF",
            font=("Segoe UI", 28, "bold"),
        ).pack(anchor="w", pady=(10, 0))
        tk.Label(
            frame,
            text="条有效信号",
            bg="#1353D8",
            fg="#FFFFFF",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            text="监听引擎已完成 A 股核心自选池扫描，当前重点跟踪买入转强与高位背离卖出信号。",
            bg="#1353D8",
            fg="#E8EEFF",
            font=("Segoe UI", 10),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))
        badge = tk.Frame(frame, bg="#2E6AEC", padx=14, pady=10)
        badge.pack(anchor="e", pady=(14, 0))
        tk.Label(
            badge,
            text="扫描轮次",
            bg="#2E6AEC",
            fg="#C9D7FF",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="e")
        tk.Label(
            badge, text="06", bg="#2E6AEC", fg="#FFFFFF", font=("Segoe UI", 22, "bold")
        ).pack(anchor="e")
        return frame

    def _metric_card(
        self,
        parent: tk.Widget,
        title: str,
        value_var: tk.StringVar,
        note: str,
        tone: str,
    ) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg="#FFFFFF",
            padx=20,
            pady=20,
            highlightbackground="#E2E8EE",
            highlightthickness=1,
        )
        tk.Label(
            frame, text=title, bg="#FFFFFF", fg="#737C81", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            frame,
            textvariable=value_var,
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w", pady=(14, 4))
        tk.Label(
            frame, text=note, bg="#FFFFFF", fg=tone, font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        return frame

    def _build_watchlist_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg="#F4F7FB")
        page.columnconfigure(0, weight=1)
        page.columnconfigure(1, weight=0)
        page.rowconfigure(0, weight=1)

        table_panel = tk.Frame(
            page, bg="#FFFFFF", highlightbackground="#E2E8EE", highlightthickness=1
        )
        table_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        table_panel.rowconfigure(1, weight=1)
        table_panel.columnconfigure(0, weight=1)

        header = tk.Frame(table_panel, bg="#FFFFFF")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        tk.Label(
            header,
            text="实时信号列表",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="高密度监控视图",
            bg="#FFFFFF",
            fg="#737C81",
            font=("Segoe UI", 9),
        ).pack(side="right")

        columns = ("code", "name", "price", "change", "signal", "time")
        self.tree = ttk.Treeview(
            table_panel, columns=columns, show="headings", style="Signal.Treeview"
        )
        headings = {
            "code": "证券代码",
            "name": "证券名称",
            "price": "最新价格",
            "change": "当日涨幅",
            "signal": "信号类型",
            "time": "触发时间",
        }
        widths = {
            "code": 120,
            "name": 120,
            "price": 110,
            "change": 110,
            "signal": 180,
            "time": 120,
        }
        anchors = {
            "code": "center",
            "name": "center",
            "price": "e",
            "change": "e",
            "signal": "center",
            "time": "e",
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            anchor = cast(Literal["center", "e"], anchors[key])
            self.tree.column(key, width=widths[key], anchor=anchor, stretch=True)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        sidebar = tk.Frame(page, bg="#F4F7FB", width=340)
        sidebar.grid(row=0, column=1, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)

        self._status_panel(sidebar).grid(row=0, column=0, sticky="ew")
        self._signal_summary_panel(sidebar).grid(
            row=1, column=0, sticky="ew", pady=(16, 0)
        )
        return page

    def _build_rules_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg="#F4F7FB")
        panel = tk.Frame(page, bg="#F4F7FB")
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(0, weight=1)

        header = tk.Frame(panel, bg="#F4F7FB")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        tk.Label(
            header,
            text="策略配置",
            bg="#F4F7FB",
            fg="#2B3438",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="设置您的自动化监听规则，系统将在触发条件时实时推送通知。",
            bg="#F4F7FB",
            fg="#586065",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 0))

        self.rule_container = tk.Frame(panel, bg="#F4F7FB")
        self.rule_container.grid(row=1, column=0, sticky="nsew")
        self.rule_container.columnconfigure(0, weight=1)

        macd_card = tk.Frame(
            self.rule_container,
            bg="#FFFFFF",
            padx=24,
            pady=24,
            highlightbackground="#E2E8EE",
            highlightthickness=1,
        )
        macd_card.grid(row=0, column=0, sticky="ew")
        self._build_macd_card(macd_card)

        divergence_card = tk.Frame(
            self.rule_container,
            bg="#FFFFFF",
            padx=24,
            pady=24,
            highlightbackground="#E2E8EE",
            highlightthickness=1,
        )
        divergence_card.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        self._build_divergence_card(divergence_card)

        tip = tk.Frame(
            self.rule_container,
            bg="#F1F4F7",
            padx=18,
            pady=16,
            highlightbackground="#DBE4EA",
            highlightthickness=1,
        )
        tip.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        tk.Label(
            tip,
            text="i",
            bg="#DBE1FF",
            fg="#1353D8",
            font=("Segoe UI", 10, "bold"),
            width=2,
        ).pack(side="left", padx=(0, 12))
        tk.Label(
            tip,
            text="提示：多条策略同时启用时，系统将并行监控并分别推送满足条件的标的。",
            bg="#F1F4F7",
            fg="#586065",
            font=("Segoe UI", 10),
        ).pack(side="left")
        return page

    def _build_macd_card(self, parent: tk.Widget) -> None:
        top = tk.Frame(parent, bg="#FFFFFF")
        top.pack(fill="x")

        badge = tk.Frame(top, bg="#DBE1FF", width=40, height=40)
        badge.pack(side="left")
        badge.pack_propagate(False)
        tk.Label(
            badge, text="M", bg="#DBE1FF", fg="#0046C3", font=("Segoe UI", 14, "bold")
        ).pack(expand=True)

        title_wrap = tk.Frame(top, bg="#FFFFFF")
        title_wrap.pack(side="left", padx=14)
        tk.Label(
            title_wrap,
            text="MACD策略",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="MACD Strategy",
            bg="#FFFFFF",
            fg="#737C81",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        ttk.Checkbutton(
            top,
            text="启用策略",
            variable=self.macd_enabled_var,
            command=self._sync_rule_state,
        ).pack(side="right")

        content = tk.Frame(parent, bg="#FFFFFF")
        content.pack(fill="x", pady=(22, 0))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        left = tk.Frame(content, bg="#FFFFFF")
        left.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        tk.Label(
            left,
            text="当日涨幅阈值",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        slider_row = tk.Frame(left, bg="#FFFFFF")
        slider_row.pack(fill="x", pady=(14, 8))
        ttk.Scale(
            slider_row,
            from_=0,
            to=20,
            variable=self.macd_threshold_var,
            command=self._on_macd_slider,
        ).pack(side="left", fill="x", expand=True)
        threshold_entry = ttk.Entry(
            slider_row,
            textvariable=self.macd_threshold_text_var,
            width=10,
            justify="right",
        )
        threshold_entry.pack(side="left", padx=(14, 0))
        threshold_entry.bind("<FocusOut>", self._on_macd_entry_commit)
        threshold_entry.bind("<Return>", self._on_macd_entry_commit)
        tk.Label(
            left,
            text="当个股当日涨幅超过此百分比时触发监控。",
            bg="#FFFFFF",
            fg="#586065",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        right = tk.Frame(content, bg="#FFFFFF")
        right.grid(row=0, column=1, sticky="ew", padx=(14, 0))
        tk.Label(
            right,
            text="零轴穿透模式",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        ttk.Combobox(
            right,
            textvariable=self.macd_mode_var,
            state="readonly",
            values=("从下方金叉穿过", "零轴上方二次金叉", "快速DIF回踩DEA"),
        ).pack(fill="x", pady=(14, 0))

    def _build_divergence_card(self, parent: tk.Widget) -> None:
        top = tk.Frame(parent, bg="#FFFFFF")
        top.pack(fill="x")

        badge = tk.Frame(top, bg="#D7F9E8", width=40, height=40)
        badge.pack(side="left")
        badge.pack_propagate(False)
        tk.Label(
            badge, text="D", bg="#D7F9E8", fg="#005A3C", font=("Segoe UI", 14, "bold")
        ).pack(expand=True)

        title_wrap = tk.Frame(top, bg="#FFFFFF")
        title_wrap.pack(side="left", padx=14)
        tk.Label(
            title_wrap,
            text="背离策略",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="Divergence Strategy",
            bg="#FFFFFF",
            fg="#737C81",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        ttk.Checkbutton(
            top,
            text="启用策略",
            variable=self.divergence_enabled_var,
            command=self._sync_rule_state,
        ).pack(side="right")

        content = tk.Frame(parent, bg="#FFFFFF")
        content.pack(fill="x", pady=(22, 0))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        left = tk.Frame(content, bg="#FFFFFF")
        left.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        tk.Label(
            left,
            text="背离周期确认",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        period_row = tk.Frame(left, bg="#FFFFFF")
        period_row.pack(fill="x", pady=(14, 0))
        for period in RULE_PERIODS:
            btn = tk.Button(
                period_row,
                text=period,
                bd=0,
                relief="flat",
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                command=lambda p=period: self._select_period(p),
            )
            btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.period_buttons[period] = btn

        right = tk.Frame(content, bg="#FFFFFF")
        right.grid(row=0, column=1, sticky="ew", padx=(14, 0))
        tk.Label(
            right,
            text="当日涨幅限制",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        ttk.Entry(right, textvariable=self.divergence_limit_var).pack(
            fill="x", pady=(14, 0)
        )

        info_grid = tk.Frame(parent, bg="#FFFFFF")
        info_grid.pack(fill="x", pady=(22, 0))
        for col in range(3):
            info_grid.columnconfigure(col, weight=1)
        self._info_tile(info_grid, 0, "价格指标", "Lower Low (新低)", "#006D4A")
        self._info_tile(info_grid, 1, "动量指标", "Higher Low (抬高)", "#1353D8")
        self._info_tile(info_grid, 2, "偏离阈值", "12.5%", "#9E3F4E")

    def _info_tile(
        self, parent: tk.Widget, column: int, title: str, value: str, accent: str
    ) -> None:
        tile = tk.Frame(
            parent,
            bg="#F1F4F7",
            padx=14,
            pady=14,
            highlightbackground=accent,
            highlightthickness=2,
        )
        tile.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        tk.Label(
            tile, text=title, bg="#F1F4F7", fg="#737C81", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        tk.Label(
            tile, text=value, bg="#F1F4F7", fg="#2B3438", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(8, 0))

    def _build_logs_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg="#F4F7FB")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)

        panel = tk.Frame(
            page, bg="#FFFFFF", highlightbackground="#E2E8EE", highlightthickness=1
        )
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        top = tk.Frame(panel, bg="#FFFFFF")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        tk.Label(
            top,
            text="系统日志",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        tk.Label(
            top,
            text="记录监听引擎最近状态变化",
            bg="#FFFFFF",
            fg="#737C81",
            font=("Segoe UI", 10),
        ).pack(side="right")

        holder = tk.Frame(panel, bg="#FFFFFF")
        holder.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)

        canvas = tk.Canvas(holder, bg="#FFFFFF", highlightthickness=0)
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        self.log_scroll_frame = tk.Frame(canvas, bg="#FFFFFF")
        self.log_scroll_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.log_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        return page

    def _status_panel(self, parent: tk.Widget) -> tk.Frame:
        panel = tk.Frame(
            parent,
            bg="#FFFFFF",
            padx=20,
            pady=20,
            highlightbackground="#E2E8EE",
            highlightthickness=1,
        )
        tk.Label(
            panel,
            text="监听状态",
            bg="#FFFFFF",
            fg="#737C81",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            panel,
            textvariable=self.status_var,
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(8, 6))
        tk.Label(
            panel,
            text="Active",
            bg="#E7FFF0",
            fg="#006D4A",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
        ).pack(anchor="e")
        for label, value in (
            ("监听市场", "沪深 A 股"),
            ("策略组合", "MACD + 背离"),
            ("通知方式", "桌面弹窗"),
        ):
            row = tk.Frame(panel, bg="#F1F4F7", padx=12, pady=12)
            row.pack(fill="x", pady=6)
            tk.Label(
                row, text=label, bg="#F1F4F7", fg="#586065", font=("Segoe UI", 10)
            ).pack(side="left")
            tk.Label(
                row,
                text=value,
                bg="#F1F4F7",
                fg="#2B3438",
                font=("Segoe UI", 10, "bold"),
            ).pack(side="right")
        return panel

    def _signal_summary_panel(self, parent: tk.Widget) -> tk.Frame:
        panel = tk.Frame(
            parent,
            bg="#FFFFFF",
            padx=20,
            pady=20,
            highlightbackground="#E2E8EE",
            highlightthickness=1,
        )
        tk.Label(
            panel,
            text="最新动态",
            bg="#FFFFFF",
            fg="#2B3438",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        self.side_log_container = tk.Frame(panel, bg="#FFFFFF")
        self.side_log_container.pack(fill="both", expand=True, pady=(12, 0))
        return panel

    def _build_footer(self) -> None:
        footer = tk.Frame(
            self.root,
            bg="#F8F9FB",
            height=52,
            highlightbackground="#E8EDF2",
            highlightthickness=1,
        )
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        tk.Label(
            footer,
            text="关于我们    服务协议    隐私政策    联系支持      © 2024 金融视界 Precision Minimalism.",
            bg="#F8F9FB",
            fg="#8A949B",
            font=("Segoe UI", 9),
        ).pack(expand=True)

    def _build_toast(self) -> None:
        self.toast = tk.Label(
            self.root,
            textvariable=self.toast_var,
            bg="#0C0F10",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=10,
        )
        self.toast.place_forget()

    def switch_page(self, page: str) -> None:
        self.active_page = page
        self.pages[page].tkraise()
        for key, label in self.nav_labels.items():
            label.configure(fg="#1353D8" if key == page else "#586065")
        if page == "rules":
            self.fab_button.configure(
                text="保存规则配置", command=self.save_rule_config
            )
        else:
            self.fab_button.configure(text="添加自选", command=self.open_add_dialog)

    def refresh_dashboard(self) -> None:
        buy_count = sum(1 for item in self.signals if item[5] == "buy")
        sell_count = sum(1 for item in self.signals if item[5] == "sell")
        total_count = len(self.signals)

        self.buy_count_var.set(str(buy_count))
        self.sell_count_var.set(str(sell_count))
        self.total_count_var.set(str(total_count))

        self._populate_table()
        self._populate_rule_cards()
        self._populate_logs()

    def _populate_table(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for signal in self.signals:
            tag = "buy" if signal[5] == "buy" else "sell"
            self.tree.insert(
                "",
                "end",
                values=(
                    signal[0],
                    signal[1],
                    signal[2],
                    signal[3],
                    signal[4],
                    signal[6],
                ),
                tags=(tag,),
            )

        self.tree.tag_configure("buy", foreground="#9E3F4E")
        self.tree.tag_configure("sell", foreground="#006D4A")

    def _populate_rule_cards(self) -> None:
        self._sync_rule_state()

    def _populate_logs(self) -> None:
        for child in self.side_log_container.winfo_children():
            child.destroy()
        for child in self.log_scroll_frame.winfo_children():
            child.destroy()

        for timestamp, message in self.logs[:5]:
            box = tk.Frame(self.side_log_container, bg="#F1F4F7", padx=12, pady=12)
            box.pack(fill="x", pady=(0, 8))
            tk.Label(
                box,
                text=message,
                bg="#F1F4F7",
                fg="#2B3438",
                font=("Segoe UI", 10),
                justify="left",
                wraplength=260,
            ).pack(anchor="w")
            tk.Label(
                box,
                text=timestamp,
                bg="#F1F4F7",
                fg="#737C81",
                font=("Consolas", 9, "bold"),
            ).pack(anchor="e", pady=(6, 0))

        for timestamp, message in self.logs:
            row = tk.Frame(
                self.log_scroll_frame,
                bg="#FFFFFF",
                padx=16,
                pady=14,
                highlightbackground="#EDF1F5",
                highlightthickness=1,
            )
            row.pack(fill="x", pady=(0, 10))
            tk.Label(
                row,
                text=message,
                bg="#FFFFFF",
                fg="#2B3438",
                font=("Segoe UI", 10),
                justify="left",
                wraplength=980,
            ).pack(anchor="w")
            tk.Label(
                row,
                text=timestamp,
                bg="#FFFFFF",
                fg="#7A848D",
                font=("Consolas", 10, "bold"),
            ).pack(anchor="e", pady=(6, 0))

    def add_signal(self, row: SignalRow) -> None:
        self.signals.insert(0, row)
        action = "卖出" if row[5] == "sell" else "买入"
        self.logs.insert(
            0, (row[6], f"{row[1]}({row[0]}) 新增 {row[4]}，已加入{action}监听列表。")
        )
        self.status_var.set(f"最新更新: {row[1]} {row[4]}")
        self.refresh_dashboard()
        self.switch_page("watchlist")
        self.show_toast(f"{row[1]} 已添加到自选列表。")

    def open_add_dialog(self) -> None:
        AddWatchlistDialog(self)

    def _on_macd_slider(self, _value: str) -> None:
        self.macd_threshold_text_var.set(f"> {self.macd_threshold_var.get():.1f}")

    def _on_macd_entry_commit(self, _event: tk.Event[tk.Widget]) -> None:
        raw = (
            self.macd_threshold_text_var.get().replace(">", "").replace("%", "").strip()
        )
        try:
            value = max(0.0, min(20.0, float(raw)))
        except ValueError:
            value = self.macd_threshold_var.get()
        self.macd_threshold_var.set(value)
        self.macd_threshold_text_var.set(f"> {value:.1f}")

    def _select_period(self, period: str) -> None:
        self.divergence_period_var.set(period)
        self._sync_rule_state()

    def _sync_rule_state(self) -> None:
        for period, button in self.period_buttons.items():
            selected = period == self.divergence_period_var.get()
            button.configure(
                bg="#1353D8" if selected else "#F1F4F7",
                fg="#FFFFFF" if selected else "#586065",
                activebackground="#0B50D5" if selected else "#E5EBF0",
                activeforeground="#FFFFFF" if selected else "#2B3438",
                padx=10,
                pady=8,
            )

    def save_rule_config(self) -> None:
        self.status_var.set("规则已更新")
        self.logs.insert(
            0,
            (
                time.strftime("%H:%M:%S"),
                f"规则配置已保存：MACD={'开' if self.macd_enabled_var.get() else '关'}，背离={'开' if self.divergence_enabled_var.get() else '关'}，周期={self.divergence_period_var.get()}。",
            ),
        )
        self._populate_logs()
        self.show_toast("规则配置已保存。")

    def show_toast(self, message: str) -> None:
        self.toast_var.set(message)
        self.toast.place(relx=0.5, y=18, anchor="n")
        self.root.after(2200, self.toast.place_forget)

    def _tick_clock(self) -> None:
        self.clock_var.set(time.strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)


def main() -> None:
    root = tk.Tk()
    StockListenerAssistant(root)
    root.mainloop()


if __name__ == "__main__":
    main()
