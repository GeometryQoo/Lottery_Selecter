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
        self.root.geometry("900x900")
        self.root.resizable(False, False)

        # 設定視窗背景色
        self.root.configure(bg='#f0f0f0')

        # 初始化資料庫連接
        self.db_path = 'lottery.db'

        # 儲存當前選號結果（用於歷史對獎）
        self.current_numbers = None

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

        # Top30選號按鈕
        smart_button = tk.Button(
            button_frame,
            text="🎲 Top30選號",
            font=('Helvetica', 18, 'bold'),
            bg='#28a745',
            fg='black',
            width=15,
            height=2,
            relief='raised',
            bd=3,
            command=self.smart_pick
        )
        smart_button.pack(side='left', padx=10)

        # Top20選號按鈕
        mixed_button = tk.Button(
            button_frame,
            text="🎯 Top20選號",
            font=('Helvetica', 18, 'bold'),
            bg='#5a67d8',
            fg='black',
            width=15,
            height=2,
            relief='raised',
            bd=3,
            command=self.mixed_pick
        )
        mixed_button.pack(side='left', padx=10)

        # 歷史對獎按鈕
        history_button = tk.Button(
            button_frame,
            text="🎖️ 歷史對獎",
            font=('Helvetica', 18, 'bold'),
            bg='#f59e0b',
            fg='black',
            width=15,
            height=2,
            relief='raised',
            bd=3,
            command=self.history_check
        )
        history_button.pack(side='left', padx=10)

        # 說明文字
        info_frame = tk.Frame(self.root, bg='#e0e7ff', bd=2, relief='solid')
        info_frame.pack(fill='x', padx=20, pady=10)

        info_text = (
            "📌 Top30選號：從 Top 30 最常出現號碼中隨機選取 6 個\n"
            "📌 Top20選號：從 Top 20 最常出現號碼中隨機選取 6 個\n"
            "📌 歷史對獎：比對已選號碼與歷年開獎記錄"
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

        # 對獎結果顯示區（初始隱藏）
        self.check_result_frame = tk.Frame(result_frame, bg='#f0f0f0')

        # 對獎統計摘要標籤
        self.check_summary_label = tk.Label(
            self.check_result_frame,
            text="",
            font=('Helvetica', 11, 'bold'),
            bg='#d1fae5',
            fg='#065f46',
            relief='solid',
            bd=1,
            padx=10,
            pady=8,
            justify='left'
        )
        self.check_summary_label.pack(fill='x', pady=(10, 5))

        # 對獎記錄表格
        check_table_frame = tk.Frame(self.check_result_frame, bg='white', relief='solid', bd=2)
        check_table_frame.pack(fill='both', expand=True)

        # 建立對獎 Treeview
        check_columns = ('期別', '開獎日期', '對中數量', '對中號碼')
        self.check_tree = ttk.Treeview(
            check_table_frame,
            columns=check_columns,
            show='headings',
            height=6
        )

        # 設定欄位寬度和標題
        self.check_tree.column('期別', width=120, anchor='center')
        self.check_tree.column('開獎日期', width=140, anchor='center')
        self.check_tree.column('對中數量', width=100, anchor='center')
        self.check_tree.column('對中號碼', width=400, anchor='center')

        for col in check_columns:
            self.check_tree.heading(col, text=col)

        # 滾動條
        check_scrollbar = ttk.Scrollbar(check_table_frame, orient='vertical', command=self.check_tree.yview)
        self.check_tree.configure(yscrollcommand=check_scrollbar.set)

        self.check_tree.pack(side='left', fill='both', expand=True)
        check_scrollbar.pack(side='right', fill='y')

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
                    num_type = 'Top30選號'

                self.tree.insert('', 'end', values=(
                    f"{num:02d}",
                    num_type,
                    stat['count'],
                    f"{stat['probability']:.2f}",
                    f"#{rank}"
                ))

    def smart_pick(self):
        """Top30選號（從 Top 30 熱門號碼中隨機選取 6 個）"""
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

        # 儲存當前選號（用於歷史對獎）
        self.current_numbers = selected

        # 繪製號碼球（全紅色）
        self.draw_number_balls(selected)

        # 更新表格
        self.update_table(selected)

        # 更新摘要
        summary_text = (
            f"📊 Top30選號結果\n"
            f"平均出現機率: {avg_prob:.2f}% | 策略: 從 Top 30 最熱門號碼中選取\n"
            f"⚠️ 注意：此選號方式不會改變中獎機率（1/13,983,816）"
        )
        self.summary_label.config(text=summary_text)

    def mixed_pick(self):
        """Top20選號（從 Top 20 熱門號碼中隨機選取 6 個）"""
        all_stats = self.get_all_numbers_stats()

        if not all_stats:
            messagebox.showerror("錯誤", "無法讀取資料")
            return

        # 取得 Top 20
        top_20 = [stat['number'] for stat in all_stats[:20]]

        # 隨機選取 6 個
        selected = sorted(random.sample(top_20, 6))

        # 計算平均機率
        stats_dict = {stat['number']: stat for stat in all_stats}
        avg_prob = sum(stats_dict[n]['probability'] for n in selected) / len(selected)

        # 儲存當前選號（用於歷史對獎）
        self.current_numbers = selected

        # 繪製號碼球（使用藍紫色）
        colors = {num: '#5a67d8' for num in selected}
        self.draw_number_balls(selected, colors)

        # 更新表格
        self.update_table(selected)

        # 更新摘要
        summary_text = (
            f"🎯 Top20選號結果\n"
            f"平均出現機率: {avg_prob:.2f}% | 策略: 從 Top 20 最熱門號碼中選取\n"
            f"⚠️ 注意：此選號方式不會改變中獎機率（1/13,983,816）"
        )
        self.summary_label.config(text=summary_text)

    def history_check(self):
        """歷史對獎功能：比對已選號碼與歷史開獎記錄"""
        # 檢查是否有選號結果
        if self.current_numbers is None:
            messagebox.showinfo(
                "提示",
                "請先使用「Top30選號」或「Top20選號」產生號碼後，再進行歷史對獎。"
            )
            return

        # 清空對獎表格
        for item in self.check_tree.get_children():
            self.check_tree.delete(item)

        try:
            # 連接資料庫
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 查詢所有大樂透開獎記錄和主號碼
            query = """
            SELECT
                d.draw_number,
                d.draw_date,
                GROUP_CONCAT(n.number) as numbers
            FROM lottery_draws d
            JOIN lottery_numbers n ON d.id = n.draw_id
            WHERE d.game_type = '大樂透' AND n.number_type = 'main'
            GROUP BY d.id, d.draw_number, d.draw_date
            ORDER BY d.draw_date DESC
            """

            cursor.execute(query)
            results = cursor.fetchall()

            # 統計資料
            total_draws = len(results)
            matches_count = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
            max_match = 0
            match_records = []

            # 比對每期開獎號碼
            for draw_number, draw_date, numbers_str in results:
                # 將開獎號碼字串轉換為整數列表
                draw_numbers = [int(n) for n in numbers_str.split(',')]

                # 計算對中數量
                matched = set(self.current_numbers) & set(draw_numbers)
                match_count = len(matched)

                # 更新最大對中數
                if match_count > max_match:
                    max_match = match_count

                # 統計各對中數量
                if match_count >= 2:
                    if match_count in matches_count:
                        matches_count[match_count] += 1

                    # 儲存對中記錄（只顯示對中2個以上）
                    match_records.append({
                        'draw_number': draw_number,
                        'draw_date': draw_date,
                        'match_count': match_count,
                        'matched_numbers': sorted(matched)
                    })

            conn.close()

            # 按對中數量降序、開獎日期降序排序
            match_records.sort(key=lambda x: (x['match_count'], x['draw_date']), reverse=True)

            # 更新對獎統計摘要
            summary_text = (
                f"🎖️ 歷史對獎結果\n"
                f"您的號碼: {', '.join([f'{n:02d}' for n in self.current_numbers])} | "
                f"總比對期數: {total_draws} 期 | 最高對中: {max_match} 個號碼\n"
                f"對中統計: "
            )

            # 添加統計詳情
            stats_parts = []
            for count in [6, 5, 4, 3, 2]:
                if matches_count[count] > 0:
                    stats_parts.append(f"{count}個={matches_count[count]}期")

            if stats_parts:
                summary_text += " | ".join(stats_parts)
            else:
                summary_text += "無符合記錄（對中數 < 2）"

            self.check_summary_label.config(text=summary_text)

            # 更新對獎表格（只顯示對中2個以上的記錄）
            for record in match_records:
                matched_str = ', '.join([f'{n:02d}' for n in record['matched_numbers']])
                self.check_tree.insert('', 'end', values=(
                    record['draw_number'],
                    record['draw_date'],
                    f"{record['match_count']} 個",
                    matched_str
                ))

            # 顯示對獎結果區域
            self.check_result_frame.pack(fill='both', expand=True, pady=(10, 0))

            # 如果沒有對中2個以上的記錄，顯示提示
            if not match_records:
                messagebox.showinfo(
                    "對獎結果",
                    f"很遺憾，您的號碼在歷史 {total_draws} 期中，\n"
                    f"最多只對中 {max_match} 個號碼，未達到最低中獎門檻（3個號碼）。"
                )

        except Exception as e:
            messagebox.showerror("錯誤", f"對獎過程發生錯誤：{str(e)}")


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
