#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大樂透智慧選號系統 GUI
支援兩種選號策略：智慧選號器 & 混合策略選號器
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import random
from typing import List, Tuple, Dict


class LotteryGUI:
    """大樂透選號 GUI 應用程式"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎰 大樂透智慧選號系統")
        self.root.geometry("850x750")
        self.root.resizable(False, False)

        # 設定視窗背景色
        self.root.configure(bg='#f0f0f0')

        # 初始化資料庫連接
        self.db_path = 'lottery.db'

        # 建立 UI
        self.create_widgets()

    def create_widgets(self):
        """建立所有 UI 元件"""

        # 標題區
        title_frame = tk.Frame(self.root, bg='#667eea', height=100)
        title_frame.pack(fill='x', padx=10, pady=10)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="🎰 大樂透智慧選號系統",
            font=('Helvetica', 28, 'bold'),
            bg='#667eea',
            fg='white'
        )
        title_label.pack(pady=10)

        subtitle_label = tk.Label(
            title_frame,
            text="基於 2007-2025 歷史資料，提供兩種選號策略",
            font=('Helvetica', 12),
            bg='#667eea',
            fg='white'
        )
        subtitle_label.pack()

        # 按鈕區
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(pady=20)

        # 智慧選號按鈕
        smart_button = tk.Button(
            button_frame,
            text="🎲 智慧選號",
            font=('Helvetica', 18, 'bold'),
            bg='#28a745',
            fg='white',
            width=15,
            height=2,
            relief='raised',
            bd=3,
            command=self.smart_pick
        )
        smart_button.pack(side='left', padx=10)

        # 混合策略選號按鈕
        mixed_button = tk.Button(
            button_frame,
            text="🎯 混合策略選號",
            font=('Helvetica', 18, 'bold'),
            bg='#5a67d8',
            fg='white',
            width=18,
            height=2,
            relief='raised',
            bd=3,
            command=self.mixed_pick
        )
        mixed_button.pack(side='left', padx=10)

        # 說明文字
        info_frame = tk.Frame(self.root, bg='#e0e7ff', bd=2, relief='solid')
        info_frame.pack(fill='x', padx=20, pady=10)

        info_text = (
            "📌 智慧選號：從 Top 30 最常出現號碼中隨機選取 6 個\n"
            "📌 混合策略：熱號3個 + 冷號2個 + 驚喜號1個"
        )
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=('Helvetica', 11),
            bg='#e0e7ff',
            fg='#4a5568',
            justify='left',
            padx=15,
            pady=10
        )
        info_label.pack()

        # 結果顯示區
        result_frame = tk.Frame(self.root, bg='#f0f0f0')
        result_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # 號碼球顯示區
        self.canvas = tk.Canvas(
            result_frame,
            height=120,
            bg='white',
            relief='solid',
            bd=2
        )
        self.canvas.pack(fill='x', pady=(0, 10))

        # 統計資訊表格
        table_frame = tk.Frame(result_frame, bg='white', relief='solid', bd=2)
        table_frame.pack(fill='both', expand=True)

        # 建立 Treeview
        columns = ('號碼', '類型', '出現次數', '機率(%)', '排名')
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=8
        )

        # 設定欄位寬度和標題
        self.tree.column('號碼', width=100, anchor='center')
        self.tree.column('類型', width=120, anchor='center')
        self.tree.column('出現次數', width=120, anchor='center')
        self.tree.column('機率(%)', width=120, anchor='center')
        self.tree.column('排名', width=100, anchor='center')

        for col in columns:
            self.tree.heading(col, text=col)

        # 滾動條
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 統計摘要區
        self.summary_label = tk.Label(
            result_frame,
            text="",
            font=('Helvetica', 11),
            bg='#fff3cd',
            fg='#856404',
            relief='solid',
            bd=1,
            padx=10,
            pady=10,
            justify='left'
        )
        self.summary_label.pack(fill='x', pady=(10, 0))

    def get_all_numbers_stats(self) -> List[Dict]:
        """從資料庫獲取所有號碼統計資料"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            SELECT
                n.number,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT draw_id) FROM lottery_numbers
                                            WHERE draw_id IN (SELECT id FROM lottery_draws WHERE game_type = '大樂透')), 2) as probability
            FROM lottery_numbers n
            JOIN lottery_draws d ON n.draw_id = d.id
            WHERE d.game_type = '大樂透'
              AND n.number_type = 'main'
            GROUP BY n.number
            ORDER BY count DESC
            """

            cursor.execute(query)
            results = []
            for row in cursor.fetchall():
                results.append({
                    'number': int(row[0]),
                    'count': int(row[1]),
                    'probability': float(row[2])
                })

            conn.close()
            return results

        except Exception as e:
            messagebox.showerror("錯誤", f"資料庫讀取失敗：{str(e)}")
            return []

    def draw_number_balls(self, numbers: List[int], colors: Dict[int, str] = None):
        """在 Canvas 上繪製號碼球"""
        self.canvas.delete('all')

        if not numbers:
            return

        # 計算位置
        ball_size = 80
        gap = 20
        total_width = len(numbers) * ball_size + (len(numbers) - 1) * gap
        start_x = (self.canvas.winfo_width() - total_width) / 2

        if start_x < 20:
            start_x = 20

        y = 60

        for i, num in enumerate(numbers):
            x = start_x + i * (ball_size + gap) + ball_size / 2

            # 決定顏色
            if colors and num in colors:
                color = colors[num]
            else:
                color = '#ff6b6b'

            # 繪製陰影
            self.canvas.create_oval(
                x - ball_size/2 + 3, y - ball_size/2 + 3,
                x + ball_size/2 + 3, y + ball_size/2 + 3,
                fill='#cccccc', outline=''
            )

            # 繪製球體
            self.canvas.create_oval(
                x - ball_size/2, y - ball_size/2,
                x + ball_size/2, y + ball_size/2,
                fill=color, outline='white', width=3
            )

            # 繪製號碼
            self.canvas.create_text(
                x, y,
                text=f"{num:02d}",
                font=('Helvetica', 28, 'bold'),
                fill='white'
            )

    def update_table(self, selected_numbers: List[int], number_types: Dict[int, str] = None):
        """更新統計表格"""
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 獲取統計資料
        all_stats = self.get_all_numbers_stats()
        stats_dict = {stat['number']: stat for stat in all_stats}

        # 填充資料
        for num in selected_numbers:
            if num in stats_dict:
                stat = stats_dict[num]
                rank = next(i for i, s in enumerate(all_stats, 1) if s['number'] == num)

                # 決定類型
                if number_types and num in number_types:
                    num_type = number_types[num]
                else:
                    num_type = '智慧選號'

                self.tree.insert('', 'end', values=(
                    f"{num:02d}",
                    num_type,
                    stat['count'],
                    f"{stat['probability']:.2f}",
                    f"#{rank}"
                ))

    def smart_pick(self):
        """智慧選號（Top 30 策略）"""
        all_stats = self.get_all_numbers_stats()

        if not all_stats:
            messagebox.showerror("錯誤", "無法讀取資料")
            return

        # 取得 Top 30
        top_30 = [stat['number'] for stat in all_stats[:30]]

        # 隨機選取 6 個
        selected = sorted(random.sample(top_30, 6))

        # 計算平均機率
        stats_dict = {stat['number']: stat for stat in all_stats}
        avg_prob = sum(stats_dict[n]['probability'] for n in selected) / len(selected)

        # 繪製號碼球（全紅色）
        self.draw_number_balls(selected)

        # 更新表格
        self.update_table(selected)

        # 更新摘要
        summary_text = (
            f"📊 智慧選號結果\n"
            f"平均出現機率: {avg_prob:.2f}% | 策略: 從 Top 30 最熱門號碼中選取\n"
            f"⚠️ 注意：此選號方式不會改變中獎機率（1/13,983,816）"
        )
        self.summary_label.config(text=summary_text)

    def mixed_pick(self):
        """混合策略選號"""
        all_stats = self.get_all_numbers_stats()

        if not all_stats:
            messagebox.showerror("錯誤", "無法讀取資料")
            return

        # 定義號碼池
        hot_numbers = [stat['number'] for stat in all_stats[:15]]  # Top 15
        cold_numbers = [stat['number'] for stat in all_stats if stat['probability'] < 11.5]

        # 選號
        selected_hot = random.sample(hot_numbers, 3)
        selected_cold = random.sample(cold_numbers, 2)

        # 驚喜號
        available = [n for n in range(1, 50) if n not in selected_hot + selected_cold]
        selected_surprise = [random.choice(available)]

        # 合併並排序
        all_selected = sorted(selected_hot + selected_cold + selected_surprise)

        # 建立類型映射和顏色映射
        number_types = {}
        colors = {}

        for num in selected_hot:
            number_types[num] = '🔴 熱號'
            colors[num] = '#ff6b6b'

        for num in selected_cold:
            number_types[num] = '🔵 冷號'
            colors[num] = '#4facfe'

        for num in selected_surprise:
            number_types[num] = '🟡 驚喜號'
            colors[num] = '#ffd700'

        # 計算平均機率
        stats_dict = {stat['number']: stat for stat in all_stats}
        avg_prob = sum(stats_dict[n]['probability'] for n in all_selected) / len(all_selected)

        # 繪製彩色號碼球
        self.draw_number_balls(all_selected, colors)

        # 更新表格
        self.update_table(all_selected, number_types)

        # 更新摘要
        summary_text = (
            f"🎯 混合策略選號結果\n"
            f"平均出現機率: {avg_prob:.2f}% | "
            f"🔴 熱號 {len(selected_hot)} 個 | 🔵 冷號 {len(selected_cold)} 個 | 🟡 驚喜號 {len(selected_surprise)} 個\n"
            f"⚠️ 注意：此選號方式不會改變中獎機率（1/13,983,816）"
        )
        self.summary_label.config(text=summary_text)


def main():
    """主程式入口"""
    try:
        # 測試 tkinter 是否正常
        test_root = tk.Tk()
        test_root.withdraw()
        test_root.destroy()

        # 啟動主程式
        root = tk.Tk()
        app = LotteryGUI(root)
        root.mainloop()

    except tk.TclError as e:
        print("\n" + "=" * 60)
        print("❌ tkinter 錯誤")
        print("=" * 60)
        print(f"\n錯誤訊息: {e}")
        print("\n可能原因：")
        print("  1. tkinter 未正確安裝")
        print("  2. 顯示環境問題")
        print("  3. 缺少 Tcl/Tk 框架")
        print("\n解決方法：")
        print("  1. 執行診斷工具：python3 檢查環境.py")
        print("  2. 重新安裝 Python：brew reinstall python@3.11")
        print("  3. 查看「故障排除指南.md」獲取詳細說明")
        print("\n" + "=" * 60)
        import sys
        sys.exit(1)

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 程式執行錯誤")
        print("=" * 60)
        print(f"\n錯誤訊息: {e}")
        print(f"錯誤類型: {type(e).__name__}")
        print("\n請執行診斷工具：python3 檢查環境.py")
        print("或查看「故障排除指南.md」")
        print("\n" + "=" * 60)

        # 顯示完整錯誤追蹤（僅在開發時）
        import traceback
        print("\n完整錯誤追蹤：")
        traceback.print_exc()

        import sys
        sys.exit(1)


if __name__ == '__main__':
    main()
