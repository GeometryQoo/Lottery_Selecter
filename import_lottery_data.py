#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票資料匯入程式
支援：大樂透、威力彩、今彩539
資料範圍：2007-2025 年
"""

import sqlite3
import csv
import os
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import sys


class LotteryImporter:
    """彩票資料匯入器"""

    # 彩票類型配置
    LOTTERY_CONFIG = {
        '大樂透': {
            'main_numbers': 6,
            'has_special': True,
            'special_column': '特別號'
        },
        '威力彩': {
            'main_numbers': 6,
            'has_special': True,
            'special_column': '第二區'
        },
        '今彩539': {
            'main_numbers': 5,
            'has_special': False,
            'special_column': None
        }
    }

    def __init__(self, db_path: str = 'lottery.db', data_dir: str = 'lottery_data'):
        """
        初始化匯入器

        Args:
            db_path: 資料庫檔案路徑
            data_dir: CSV 資料目錄
        """
        self.db_path = db_path
        self.data_dir = Path(data_dir)
        self.conn = None
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'total_draws': 0,
            'total_numbers': 0,
            'errors': []
        }

    def create_schema(self):
        """建立資料庫結構"""
        print("📊 建立資料庫結構...")

        cursor = self.conn.cursor()

        # 建立主表：lottery_draws
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_type TEXT NOT NULL,
                draw_number TEXT NOT NULL,
                draw_date DATE NOT NULL,
                sales_amount INTEGER,
                sales_bets INTEGER,
                total_prize INTEGER,
                year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_type, draw_number)
            )
        ''')

        # 建立號碼表：lottery_numbers
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draw_id INTEGER NOT NULL,
                number INTEGER NOT NULL,
                number_type TEXT NOT NULL CHECK(number_type IN ('main', 'special')),
                position INTEGER,
                FOREIGN KEY (draw_id) REFERENCES lottery_draws(id) ON DELETE CASCADE
            )
        ''')

        # 建立索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_draws_game_type
            ON lottery_draws(game_type)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_draws_year
            ON lottery_draws(year)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_draws_date
            ON lottery_draws(draw_date)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_draws_number
            ON lottery_draws(draw_number)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_numbers_draw_id
            ON lottery_numbers(draw_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_numbers_value
            ON lottery_numbers(number)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_numbers_type
            ON lottery_numbers(number_type)
        ''')

        self.conn.commit()
        print("✅ 資料庫結構建立完成")

    def connect(self):
        """連接資料庫"""
        self.conn = sqlite3.connect(self.db_path)
        # 啟用外鍵約束
        self.conn.execute('PRAGMA foreign_keys = ON')
        print(f"🔗 已連接到資料庫：{self.db_path}")

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            print("🔌 已關閉資料庫連接")

    def scan_csv_files(self) -> List[Tuple[str, Path]]:
        """
        掃描所有 CSV 檔案

        Returns:
            List of (game_type, file_path) tuples
        """
        files = []

        if not self.data_dir.exists():
            print(f"❌ 錯誤：找不到資料目錄 {self.data_dir}")
            return files

        # 掃描所有年份目錄
        for year_dir in sorted(self.data_dir.iterdir()):
            if not year_dir.is_dir():
                continue

            # 掃描每個彩票類型
            for game_type in self.LOTTERY_CONFIG.keys():
                # 尋找該年份的彩票檔案
                pattern = f"{game_type}_*.csv"
                for csv_file in year_dir.glob(pattern):
                    # 確保檔案名稱與彩票類型精確匹配（避免匹配到「大樂透加開獎項」等檔案）
                    filename = csv_file.stem  # 不含副檔名的檔名
                    # 檢查是否為精確匹配：「彩票名稱_年份」或「彩票名稱_年月_年月」格式
                    if filename.startswith(f"{game_type}_") and not filename.startswith(f"{game_type}加"):
                        files.append((game_type, csv_file))

        return files

    def parse_date(self, date_str: str) -> str:
        """
        解析日期字串

        Args:
            date_str: 日期字串，格式如 '2007/01/02'

        Returns:
            ISO 格式日期字串 'YYYY-MM-DD'
        """
        try:
            # 處理 YYYY/MM/DD 格式
            dt = datetime.strptime(date_str, '%Y/%m/%d')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            # 如果解析失敗，返回原字串
            return date_str

    def import_csv(self, game_type: str, csv_path: Path) -> int:
        """
        匯入單個 CSV 檔案

        Args:
            game_type: 彩票類型
            csv_path: CSV 檔案路徑

        Returns:
            匯入的記錄數
        """
        config = self.LOTTERY_CONFIG[game_type]
        cursor = self.conn.cursor()
        imported_count = 0

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # 提取基本資訊
                        draw_number = row['期別'].strip()
                        draw_date = self.parse_date(row['開獎日期'].strip())
                        year = int(draw_date.split('-')[0])

                        # 提取銷售資訊（可能為空）
                        sales_amount = int(row['銷售總額']) if row.get('銷售總額', '').strip() else None
                        sales_bets = int(row['銷售注數']) if row.get('銷售注數', '').strip() else None
                        total_prize = int(row['總獎金']) if row.get('總獎金', '').strip() else None

                        # 檢查是否已存在（需要同時匹配彩票類型和期別）
                        cursor.execute(
                            'SELECT id FROM lottery_draws WHERE game_type = ? AND draw_number = ?',
                            (game_type, draw_number)
                        )
                        existing = cursor.fetchone()

                        if existing:
                            # 更新現有記錄
                            draw_id = existing[0]
                            cursor.execute('''
                                UPDATE lottery_draws
                                SET game_type = ?, draw_date = ?, sales_amount = ?,
                                    sales_bets = ?, total_prize = ?, year = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (game_type, draw_date, sales_amount, sales_bets,
                                  total_prize, year, draw_id))

                            # 刪除舊的號碼記錄
                            cursor.execute('DELETE FROM lottery_numbers WHERE draw_id = ?', (draw_id,))
                        else:
                            # 插入新記錄
                            cursor.execute('''
                                INSERT INTO lottery_draws
                                (game_type, draw_number, draw_date, sales_amount,
                                 sales_bets, total_prize, year)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (game_type, draw_number, draw_date, sales_amount,
                                  sales_bets, total_prize, year))

                            draw_id = cursor.lastrowid

                        # 插入主號碼
                        for i in range(1, config['main_numbers'] + 1):
                            number_str = row[f'獎號{i}'].strip()
                            if number_str:
                                number = int(number_str)
                                cursor.execute('''
                                    INSERT INTO lottery_numbers
                                    (draw_id, number, number_type, position)
                                    VALUES (?, ?, 'main', ?)
                                ''', (draw_id, number, i))
                                self.stats['total_numbers'] += 1

                        # 插入特別號（如果有）
                        if config['has_special']:
                            special_col = config['special_column']
                            if special_col in row and row[special_col].strip():
                                special_number = int(row[special_col].strip())
                                cursor.execute('''
                                    INSERT INTO lottery_numbers
                                    (draw_id, number, number_type, position)
                                    VALUES (?, ?, 'special', 1)
                                ''', (draw_id, special_number))
                                self.stats['total_numbers'] += 1

                        imported_count += 1
                        self.stats['total_draws'] += 1

                    except Exception as e:
                        error_msg = f"處理記錄時發生錯誤 ({csv_path.name}, 期別: {row.get('期別', 'N/A')}): {str(e)}"
                        self.stats['errors'].append(error_msg)
                        print(f"  ⚠️  {error_msg}")
                        continue

            self.conn.commit()
            return imported_count

        except Exception as e:
            error_msg = f"讀取檔案時發生錯誤 ({csv_path}): {str(e)}"
            self.stats['errors'].append(error_msg)
            print(f"  ❌ {error_msg}")
            return 0

    def import_all(self):
        """匯入所有資料"""
        print("\n🔍 掃描 CSV 檔案...")
        files = self.scan_csv_files()
        self.stats['total_files'] = len(files)

        if not files:
            print("❌ 沒有找到任何 CSV 檔案")
            return

        print(f"📁 找到 {len(files)} 個檔案\n")

        # 按彩票類型分組
        files_by_type = {}
        for game_type, file_path in files:
            if game_type not in files_by_type:
                files_by_type[game_type] = []
            files_by_type[game_type].append(file_path)

        # 逐個彩票類型匯入
        for game_type, file_list in files_by_type.items():
            print(f"\n{'='*60}")
            print(f"📦 匯入 {game_type} 資料（共 {len(file_list)} 個檔案）")
            print(f"{'='*60}\n")

            for i, file_path in enumerate(sorted(file_list), 1):
                print(f"  [{i}/{len(file_list)}] 處理 {file_path.name}...", end=' ')

                count = self.import_csv(game_type, file_path)

                if count > 0:
                    print(f"✅ 匯入 {count} 筆記錄")
                    self.stats['processed_files'] += 1
                else:
                    print(f"⚠️  跳過")
                    self.stats['skipped_files'] += 1

    def print_summary(self):
        """印出統計摘要"""
        print(f"\n{'='*60}")
        print("📊 匯入統計摘要")
        print(f"{'='*60}\n")
        print(f"  總檔案數：{self.stats['total_files']}")
        print(f"  成功處理：{self.stats['processed_files']}")
        print(f"  跳過檔案：{self.stats['skipped_files']}")
        print(f"  開獎記錄：{self.stats['total_draws']}")
        print(f"  號碼記錄：{self.stats['total_numbers']}")

        if self.stats['errors']:
            print(f"\n  ⚠️  錯誤數量：{len(self.stats['errors'])}")
            print("\n  錯誤詳情：")
            for error in self.stats['errors'][:10]:  # 只顯示前 10 個錯誤
                print(f"    • {error}")
            if len(self.stats['errors']) > 10:
                print(f"    ... 還有 {len(self.stats['errors']) - 10} 個錯誤")

        print(f"\n{'='*60}\n")

    def verify_data(self):
        """驗證資料完整性"""
        print("\n🔍 驗證資料完整性...\n")

        cursor = self.conn.cursor()

        # 統計各彩票類型的記錄數
        cursor.execute('''
            SELECT game_type,
                   COUNT(*) as total,
                   MIN(year) as min_year,
                   MAX(year) as max_year
            FROM lottery_draws
            GROUP BY game_type
            ORDER BY game_type
        ''')

        print("各彩票類型統計：")
        print(f"{'彩票類型':<15} {'記錄數':<10} {'年份範圍'}")
        print("-" * 40)

        for row in cursor.fetchall():
            game_type, total, min_year, max_year = row
            print(f"{game_type:<15} {total:<10} {min_year}-{max_year}")

        # 統計號碼記錄
        cursor.execute('''
            SELECT COUNT(*) FROM lottery_numbers
        ''')
        total_numbers = cursor.fetchone()[0]
        print(f"\n號碼記錄總數：{total_numbers}\n")


def main():
    """主程式"""
    print("\n" + "="*60)
    print("  彩票資料匯入程式 v1.0")
    print("  支援：大樂透、威力彩、今彩539")
    print("="*60 + "\n")

    # 建立匯入器
    importer = LotteryImporter(
        db_path='lottery.db',
        data_dir='lottery_data'
    )

    try:
        # 連接資料庫
        importer.connect()

        # 建立資料庫結構
        importer.create_schema()

        # 匯入所有資料
        importer.import_all()

        # 印出統計摘要
        importer.print_summary()

        # 驗證資料
        importer.verify_data()

        print("🎉 資料匯入完成！\n")

    except Exception as e:
        print(f"\n❌ 發生錯誤：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # 關閉資料庫連接
        importer.close()


if __name__ == '__main__':
    main()
