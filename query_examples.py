#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彩票資料查詢範例
提供常用的統計分析功能
"""

import sqlite3
from datetime import datetime


class LotteryQuery:
    """彩票資料查詢器"""

    def __init__(self, db_path: str = 'lottery.db'):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """連接資料庫"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # 使用字典式訪問
        return self

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_number_frequency(self, game_type: str, number_type: str = 'main',
                            year_start: int = None, year_end: int = None,
                            limit: int = 10):
        """
        查詢號碼出現頻率

        Args:
            game_type: 彩票類型（'大樂透', '威力彩', '今彩539'）
            number_type: 號碼類型（'main' 主號碼, 'special' 特別號）
            year_start: 起始年份（含）
            year_end: 結束年份（含）
            limit: 返回前 N 個最常出現的號碼

        Returns:
            List of (number, count) tuples
        """
        query = '''
            SELECT n.number, COUNT(*) as count
            FROM lottery_numbers n
            JOIN lottery_draws d ON n.draw_id = d.id
            WHERE d.game_type = ? AND n.number_type = ?
        '''
        params = [game_type, number_type]

        if year_start:
            query += ' AND d.year >= ?'
            params.append(year_start)

        if year_end:
            query += ' AND d.year <= ?'
            params.append(year_end)

        query += '''
            GROUP BY n.number
            ORDER BY count DESC, n.number ASC
            LIMIT ?
        '''
        params.append(limit)

        cursor = self.conn.execute(query, params)
        return [(row['number'], row['count']) for row in cursor.fetchall()]

    def get_latest_draws(self, game_type: str, limit: int = 10):
        """
        查詢最近的開獎記錄

        Args:
            game_type: 彩票類型
            limit: 返回最近 N 期

        Returns:
            List of dict with draw info and numbers
        """
        query = '''
            SELECT d.*, GROUP_CONCAT(n.number || ':' || n.number_type, ',') as numbers
            FROM lottery_draws d
            LEFT JOIN lottery_numbers n ON d.id = n.draw_id
            WHERE d.game_type = ?
            GROUP BY d.id
            ORDER BY d.draw_date DESC, d.draw_number DESC
            LIMIT ?
        '''

        cursor = self.conn.execute(query, [game_type, limit])
        results = []

        for row in cursor.fetchall():
            # 解析號碼
            main_numbers = []
            special_numbers = []

            if row['numbers']:
                for num_info in row['numbers'].split(','):
                    num, num_type = num_info.split(':')
                    if num_type == 'main':
                        main_numbers.append(int(num))
                    else:
                        special_numbers.append(int(num))

            results.append({
                'draw_number': row['draw_number'],
                'draw_date': row['draw_date'],
                'main_numbers': sorted(main_numbers),
                'special_numbers': sorted(special_numbers),
                'sales_amount': row['sales_amount'],
                'total_prize': row['total_prize']
            })

        return results

    def get_number_combination_frequency(self, game_type: str, numbers: list,
                                        year_start: int = None, year_end: int = None):
        """
        查詢特定號碼組合同時出現的次數

        Args:
            game_type: 彩票類型
            numbers: 號碼列表
            year_start: 起始年份
            year_end: 結束年份

        Returns:
            出現次數
        """
        # 建立查詢條件
        placeholders = ','.join(['?' for _ in numbers])

        query = f'''
            SELECT COUNT(DISTINCT d.id) as count
            FROM lottery_draws d
            WHERE d.game_type = ?
            AND d.id IN (
                SELECT draw_id
                FROM lottery_numbers
                WHERE number IN ({placeholders})
                AND number_type = 'main'
                GROUP BY draw_id
                HAVING COUNT(DISTINCT number) = ?
            )
        '''
        params = [game_type] + numbers + [len(numbers)]

        if year_start:
            query += ' AND d.year >= ?'
            params.append(year_start)

        if year_end:
            query += ' AND d.year <= ?'
            params.append(year_end)

        cursor = self.conn.execute(query, params)
        return cursor.fetchone()['count']

    def get_statistics_by_year(self, game_type: str):
        """
        查詢各年份統計資料

        Args:
            game_type: 彩票類型

        Returns:
            List of yearly statistics
        """
        query = '''
            SELECT
                year,
                COUNT(*) as draw_count,
                SUM(sales_amount) as total_sales,
                SUM(total_prize) as total_prize,
                AVG(sales_amount) as avg_sales,
                AVG(total_prize) as avg_prize,
                MAX(total_prize) as max_prize,
                MIN(total_prize) as min_prize
            FROM lottery_draws
            WHERE game_type = ?
            GROUP BY year
            ORDER BY year
        '''

        cursor = self.conn.execute(query, [game_type])
        return [dict(row) for row in cursor.fetchall()]

    def get_cold_hot_numbers(self, game_type: str, recent_draws: int = 100):
        """
        查詢冷熱號碼（最近 N 期）

        Args:
            game_type: 彩票類型
            recent_draws: 最近幾期

        Returns:
            Dict with hot_numbers and cold_numbers
        """
        query = '''
            WITH recent_draws AS (
                SELECT id
                FROM lottery_draws
                WHERE game_type = ?
                ORDER BY draw_date DESC, draw_number DESC
                LIMIT ?
            )
            SELECT n.number, COUNT(*) as count
            FROM lottery_numbers n
            WHERE n.draw_id IN (SELECT id FROM recent_draws)
            AND n.number_type = 'main'
            GROUP BY n.number
            ORDER BY count DESC, n.number ASC
        '''

        cursor = self.conn.execute(query, [game_type, recent_draws])
        results = [(row['number'], row['count']) for row in cursor.fetchall()]

        # 熱號（前10個）
        hot_numbers = results[:10]

        # 冷號（後10個）
        cold_numbers = results[-10:] if len(results) >= 10 else results

        return {
            'hot_numbers': hot_numbers,
            'cold_numbers': cold_numbers
        }


def main():
    """示範查詢功能"""
    print("\n" + "="*60)
    print("  彩票資料查詢範例")
    print("="*60 + "\n")

    with LotteryQuery() as query:
        # 1. 查詢大樂透號碼出現頻率（前10名）
        print("📊 大樂透主號碼出現頻率（歷年Top 10）：\n")
        freq = query.get_number_frequency('大樂透', 'main', limit=10)
        for i, (number, count) in enumerate(freq, 1):
            print(f"  {i:2d}. 號碼 {number:2d} - 出現 {count:4d} 次")

        # 2. 查詢最近5期開獎記錄
        print("\n" + "-"*60)
        print("\n📅 大樂透最近 5 期開獎記錄：\n")
        latest = query.get_latest_draws('大樂透', limit=5)
        for draw in latest:
            main_nums = ', '.join([f"{n:02d}" for n in draw['main_numbers']])
            special_nums = ', '.join([f"{n:02d}" for n in draw['special_numbers']])
            print(f"  期別：{draw['draw_number']} ({draw['draw_date']})")
            print(f"  號碼：{main_nums} + 特別號 {special_nums}")
            print(f"  銷售額：${draw['sales_amount']:,}")
            print()

        # 3. 查詢威力彩2023年統計
        print("-"*60)
        print("\n📈 威力彩各年份統計：\n")
        stats = query.get_statistics_by_year('威力彩')
        print(f"{'年份':<6} {'期數':<6} {'總銷售額':>15} {'總獎金':>15} {'平均銷售額':>15}")
        print("-"*65)
        for stat in stats[-5:]:  # 只顯示最近5年
            if stat['year']:
                print(f"{stat['year']:<6} {stat['draw_count']:<6} "
                      f"${stat['total_sales']:>14,} ${stat['total_prize']:>14,} "
                      f"${stat['avg_sales']:>14,.0f}")

        # 4. 查詢今彩539冷熱號碼
        print("\n" + "-"*60)
        print("\n🔥 今彩539 冷熱號碼（最近100期）：\n")
        cold_hot = query.get_cold_hot_numbers('今彩539', recent_draws=100)

        print("熱號（前10名）：")
        for number, count in cold_hot['hot_numbers']:
            print(f"  號碼 {number:2d} - 出現 {count:3d} 次")

        print("\n冷號（後10名）：")
        for number, count in cold_hot['cold_numbers']:
            print(f"  號碼 {number:2d} - 出現 {count:3d} 次")

        # 5. 查詢特定號碼組合
        print("\n" + "-"*60)
        print("\n🔍 查詢大樂透號碼組合 [1, 2, 3] 同時出現的次數：\n")
        combo_count = query.get_number_combination_frequency('大樂透', [1, 2, 3])
        print(f"  號碼 1, 2, 3 同時出現：{combo_count} 次")

        print("\n" + "="*60)
        print("\n✨ 查詢完成！您可以參考 query_examples.py 自訂查詢邏輯。\n")


if __name__ == '__main__':
    main()
