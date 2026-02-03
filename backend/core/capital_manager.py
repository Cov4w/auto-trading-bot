"""
Capital Manager
===============
업비트 API를 통한 실제 입출금 내역 조회 및 원금 계산
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .exchange_manager import ExchangeManager

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """프로젝트 루트 경로 반환"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    return project_root


PROJECT_ROOT = get_project_root()


class CapitalManager:
    """업비트 API 기반 입출금 내역 관리"""

    def __init__(self, exchange=None, db_path: str = None):
        self.exchange = exchange  # ExchangeManager 인스턴스
        if db_path is None:
            db_path = str(PROJECT_ROOT / "data" / "capital.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"✅ CapitalManager initialized at {db_path}")

    def _init_database(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    amount REAL NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    amount REAL NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_deposit(self, amount: float, note: str = "") -> int:
        """입금 기록"""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO deposits (timestamp, amount, note, created_at) VALUES (?, ?, ?, ?)",
                (timestamp, amount, note, timestamp)
            )
            conn.commit()
            logger.info(f"💰 입금 기록: {amount:,.0f} 원 - {note}")
            return cursor.lastrowid

    def add_withdrawal(self, amount: float, note: str = "") -> int:
        """출금 기록"""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO withdrawals (timestamp, amount, note, created_at) VALUES (?, ?, ?, ?)",
                (timestamp, amount, note, timestamp)
            )
            conn.commit()
            logger.info(f"💸 출금 기록: {amount:,.0f} 원 - {note}")
            return cursor.lastrowid

    def get_total_deposits(self) -> float:
        """총 입금액 (업비트 API에서 가져오기)"""
        if self.exchange is None:
            logger.warning("⚠️ Exchange not set, using DB fallback")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(amount) FROM deposits")
                result = cursor.fetchone()[0]
                return result if result else 0.0

        try:
            deposits = self.exchange.get_krw_deposits(limit=1000)
            total = sum(float(d.get('amount', 0)) for d in deposits if d.get('state') == 'ACCEPTED')
            logger.info(f"💰 총 입금액 (API): {total:,.0f} 원 ({len(deposits)}건)")
            return total
        except Exception as e:
            logger.error(f"❌ API 입금 조회 실패, DB 사용: {e}")
            # Fallback to DB
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(amount) FROM deposits")
                result = cursor.fetchone()[0]
                return result if result else 0.0

    def get_total_withdrawals(self) -> float:
        """총 출금액 (업비트 API에서 가져오기)"""
        if self.exchange is None:
            logger.warning("⚠️ Exchange not set, using DB fallback")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(amount) FROM withdrawals")
                result = cursor.fetchone()[0]
                return result if result else 0.0

        try:
            withdrawals = self.exchange.get_krw_withdrawals(limit=1000)
            # Upbit에서는 수수료 제외한 실제 출금액
            total = sum(float(w.get('amount', 0)) for w in withdrawals if w.get('state') == 'DONE')
            logger.info(f"💸 총 출금액 (API): {total:,.0f} 원 ({len(withdrawals)}건)")
            return total
        except Exception as e:
            logger.error(f"❌ API 출금 조회 실패, DB 사용: {e}")
            # Fallback to DB
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(amount) FROM withdrawals")
                result = cursor.fetchone()[0]
                return result if result else 0.0

    def get_net_capital(self) -> float:
        """순 원금 (입금 - 출금) - API 기반"""
        deposits = self.get_total_deposits()
        withdrawals = self.get_total_withdrawals()
        net = deposits - withdrawals
        logger.info(f"📊 순 원금 (API): 입금 {deposits:,.0f} - 출금 {withdrawals:,.0f} = {net:,.0f} 원")
        return net

    def get_deposit_history(self, limit: int = 100) -> List[Dict]:
        """입금 내역 조회"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM deposits ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_withdrawal_history(self, limit: int = 100) -> List[Dict]:
        """출금 내역 조회"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM withdrawals ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_transactions(self, limit: int = 100) -> List[Dict]:
        """전체 입출금 내역 조회"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # UNION으로 입금/출금 합치기
            cursor = conn.execute("""
                SELECT
                    'deposit' as type,
                    timestamp,
                    amount,
                    note,
                    created_at
                FROM deposits
                UNION ALL
                SELECT
                    'withdrawal' as type,
                    timestamp,
                    amount,
                    note,
                    created_at
                FROM withdrawals
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def delete_deposit(self, deposit_id: int) -> bool:
        """입금 기록 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM deposits WHERE id = ?", (deposit_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_withdrawal(self, withdrawal_id: int) -> bool:
        """출금 기록 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM withdrawals WHERE id = ?", (withdrawal_id,))
            conn.commit()
            return cursor.rowcount > 0
