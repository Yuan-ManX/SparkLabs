"""
SparkLabs Engine - Banking & Vault System

Provides in-game banking services including player accounts, deposits,
withdrawals, interest accrual, loans with repayment schedules, safe deposit
boxes for item storage, currency exchange, and full transaction auditing.
Designed as a self-contained singleton system with seed data for immediate
integration testing.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


_MAX_ACCOUNTS = 5000
_MAX_LOANS = 2000
_MAX_BOXES = 3000
_MAX_TRANSACTIONS = 50000
_MAX_BOX_ITEMS = 200


def _evict_fifo_list(items: List[Any], key_attr: str, max_size: int) -> None:
    while len(items) > max_size:
        items.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            result[field_name] = _dataclass_to_dict(value)
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    PREMIUM = "premium"
    GUILD = "guild"
    ESCROW = "escrow"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    INTEREST = "interest"
    LOAN_DISBURSEMENT = "loan_disbursement"
    LOAN_REPAYMENT = "loan_repayment"
    FEE = "fee"
    REWARD = "reward"
    EXCHANGE_IN = "exchange_in"
    EXCHANGE_OUT = "exchange_out"
    BOX_RENT = "box_rent"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class LoanStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAID_OFF = "paid_off"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"


class BoxSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"


class BoxAccessLevel(str, Enum):
    OWNER = "owner"
    CO_OWNER = "co_owner"
    GUEST = "guest"


class BankingEventKind(str, Enum):
    ACCOUNT_OPENED = "account_opened"
    ACCOUNT_CLOSED = "account_closed"
    ACCOUNT_FROZEN = "account_frozen"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    INTEREST_ACCRUED = "interest_accrued"
    LOAN_REQUESTED = "loan_requested"
    LOAN_APPROVED = "loan_approved"
    LOAN_REJECTED = "loan_rejected"
    LOAN_REPAID = "loan_repaid"
    LOAN_DEFAULTED = "loan_defaulted"
    BOX_RENTED = "box_rented"
    BOX_OPENED = "box_opened"
    BOX_CLOSED = "box_closed"
    ITEM_STORED = "item_stored"
    ITEM_RETRIEVED = "item_retrieved"
    EXCHANGE = "exchange"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BankAccount:
    account_id: str
    owner_id: str
    account_type: str
    balance: float
    currency: str = "gold"
    status: str = "active"
    created_at: float = field(default_factory=_now)
    last_interest_at: float = field(default_factory=_now)
    interest_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "owner_id": self.owner_id,
            "account_type": self.account_type,
            "balance": self.balance,
            "currency": self.currency,
            "status": self.status,
            "created_at": self.created_at,
            "last_interest_at": self.last_interest_at,
            "interest_rate": self.interest_rate,
            "metadata": dict(self.metadata),
        }


@dataclass
class Transaction:
    tx_id: str
    account_id: str
    tx_type: str
    amount: float
    currency: str
    description: str = ""
    related_account_id: Optional[str] = None
    related_player_id: Optional[str] = None
    status: str = "completed"
    created_at: float = field(default_factory=_now)
    completed_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "account_id": self.account_id,
            "tx_type": self.tx_type,
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "related_account_id": self.related_account_id,
            "related_player_id": self.related_player_id,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class LoanPayment:
    payment_id: str
    amount: float
    principal_portion: float
    interest_portion: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "amount": self.amount,
            "principal_portion": self.principal_portion,
            "interest_portion": self.interest_portion,
            "timestamp": self.timestamp,
        }


@dataclass
class Loan:
    loan_id: str
    borrower_id: str
    principal: float
    interest_rate: float
    term_months: int
    remaining_principal: float
    remaining_interest: float
    status: str = "pending"
    disbursement_date: Optional[float] = None
    due_date: Optional[float] = None
    payments: List[LoanPayment] = field(default_factory=list)
    collateral: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "borrower_id": self.borrower_id,
            "principal": self.principal,
            "interest_rate": self.interest_rate,
            "term_months": self.term_months,
            "remaining_principal": self.remaining_principal,
            "remaining_interest": self.remaining_interest,
            "status": self.status,
            "disbursement_date": self.disbursement_date,
            "due_date": self.due_date,
            "payments": [p.to_dict() for p in self.payments],
            "collateral": self.collateral,
            "metadata": dict(self.metadata),
        }


@dataclass
class BoxItem:
    item_id: str
    name: str
    quantity: int = 1
    rarity: str = "common"
    description: str = ""
    stored_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "quantity": self.quantity,
            "rarity": self.rarity,
            "description": self.description,
            "stored_at": self.stored_at,
        }


@dataclass
class BoxAccessEntry:
    player_id: str
    player_name: str
    access_level: str
    granted_at: float = field(default_factory=_now)
    granted_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "access_level": self.access_level,
            "granted_at": self.granted_at,
            "granted_by": self.granted_by,
        }


@dataclass
class SafeDepositBox:
    box_id: str
    owner_id: str
    size: str
    contents: List[BoxItem] = field(default_factory=list)
    access_list: List[BoxAccessEntry] = field(default_factory=list)
    rent_paid_until: float = 0.0
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "box_id": self.box_id,
            "owner_id": self.owner_id,
            "size": self.size,
            "contents": [c.to_dict() for c in self.contents],
            "access_list": [a.to_dict() for a in self.access_list],
            "rent_paid_until": self.rent_paid_until,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class ExchangeRate:
    from_currency: str
    to_currency: str
    rate: float
    fee_percent: float = 0.0
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "rate": self.rate,
            "fee_percent": self.fee_percent,
            "updated_at": self.updated_at,
        }


@dataclass
class BankingConfig:
    max_accounts_per_player: int = 5
    max_loan_amount: float = 1000000.0
    base_interest_rate: float = 0.02
    savings_interest_rate: float = 0.05
    premium_interest_rate: float = 0.08
    loan_interest_rate: float = 0.12
    late_fee_percent: float = 0.05
    box_rent_small: float = 50.0
    box_rent_medium: float = 150.0
    box_rent_large: float = 400.0
    box_rent_huge: float = 1000.0
    box_rent_duration: float = 2592000.0  # 30 days in seconds
    transfer_fee_percent: float = 0.01
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_accounts_per_player": self.max_accounts_per_player,
            "max_loan_amount": self.max_loan_amount,
            "base_interest_rate": self.base_interest_rate,
            "savings_interest_rate": self.savings_interest_rate,
            "premium_interest_rate": self.premium_interest_rate,
            "loan_interest_rate": self.loan_interest_rate,
            "late_fee_percent": self.late_fee_percent,
            "box_rent_small": self.box_rent_small,
            "box_rent_medium": self.box_rent_medium,
            "box_rent_large": self.box_rent_large,
            "box_rent_huge": self.box_rent_huge,
            "box_rent_duration": self.box_rent_duration,
            "transfer_fee_percent": self.transfer_fee_percent,
            "tick_rate_hz": self.tick_rate_hz,
        }


@dataclass
class BankingStats:
    total_accounts: int = 0
    total_balance: float = 0.0
    total_loans: int = 0
    total_outstanding_loan: float = 0.0
    total_boxes: int = 0
    total_transactions: int = 0
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0
    total_interest_paid: float = 0.0
    total_fees_collected: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_accounts": self.total_accounts,
            "total_balance": self.total_balance,
            "total_loans": self.total_loans,
            "total_outstanding_loan": self.total_outstanding_loan,
            "total_boxes": self.total_boxes,
            "total_transactions": self.total_transactions,
            "total_deposits": self.total_deposits,
            "total_withdrawals": self.total_withdrawals,
            "total_interest_paid": self.total_interest_paid,
            "total_fees_collected": self.total_fees_collected,
        }


@dataclass
class BankingSnapshot:
    config: BankingConfig
    stats: BankingStats
    accounts: List[BankAccount]
    transactions: List[Transaction]
    loans: List[Loan]
    boxes: List[SafeDepositBox]
    exchange_rates: List[ExchangeRate]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "stats": self.stats.to_dict(),
            "accounts": [a.to_dict() for a in self.accounts],
            "transactions": [t.to_dict() for t in self.transactions],
            "loans": [l.to_dict() for l in self.loans],
            "boxes": [b.to_dict() for b in self.boxes],
            "exchange_rates": [r.to_dict() for r in self.exchange_rates],
        }


@dataclass
class BankingEvent:
    event_id: str
    event_type: str
    timestamp: float
    account_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "account_id": self.account_id,
            "description": self.description,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Banking & Vault System singleton
# ---------------------------------------------------------------------------

class BankingVaultSystem:
    """Singleton banking and vault system managing accounts, loans, boxes."""

    _instance: Optional["BankingVaultSystem"] = None
    _instance_lock = threading.RLock()

    def __new__(cls) -> "BankingVaultSystem":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        with _LOCK:
            if getattr(self, "_initialized", False):
                return
            self._config = BankingConfig()
            self._stats = BankingStats()
            self._accounts: Dict[str, BankAccount] = {}
            self._transactions: List[Transaction] = []
            self._loans: Dict[str, Loan] = {}
            self._boxes: Dict[str, SafeDepositBox] = {}
            self._exchange_rates: Dict[str, ExchangeRate] = {}
            self._events: List[BankingEvent] = []
            self._tick_count: int = 0
            self._initialized = False
            self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial accounts, transactions, loans, boxes, exchange rates."""
        now = _now()

        # Accounts
        acc1 = BankAccount(
            account_id="acc_starter_01",
            owner_id="player_starter",
            account_type=AccountType.SAVINGS.value,
            balance=15000.0,
            currency="gold",
            interest_rate=self._config.savings_interest_rate,
            metadata={"name": "Starter Savings"},
        )
        acc2 = BankAccount(
            account_id="acc_starter_02",
            owner_id="player_starter",
            account_type=AccountType.CHECKING.value,
            balance=2500.0,
            currency="gold",
            interest_rate=self._config.base_interest_rate,
            metadata={"name": "Starter Checking"},
        )
        acc3 = BankAccount(
            account_id="acc_guild_01",
            owner_id="guild_starter",
            account_type=AccountType.GUILD.value,
            balance=75000.0,
            currency="gold",
            interest_rate=self._config.base_interest_rate,
            metadata={"name": "Guild Treasury"},
        )
        acc4 = BankAccount(
            account_id="acc_premium_01",
            owner_id="player_premium",
            account_type=AccountType.PREMIUM.value,
            balance=320000.0,
            currency="gold",
            interest_rate=self._config.premium_interest_rate,
            metadata={"name": "Premium Vault"},
        )
        for acc in (acc1, acc2, acc3, acc4):
            self._accounts[acc.account_id] = acc

        # Transactions
        tx1 = Transaction(
            tx_id="tx_starter_01",
            account_id="acc_starter_01",
            tx_type=TransactionType.DEPOSIT.value,
            amount=15000.0,
            currency="gold",
            description="Initial deposit",
        )
        tx2 = Transaction(
            tx_id="tx_starter_02",
            account_id="acc_starter_02",
            tx_type=TransactionType.DEPOSIT.value,
            amount=2500.0,
            currency="gold",
            description="Initial deposit",
        )
        tx3 = Transaction(
            tx_id="tx_starter_03",
            account_id="acc_starter_01",
            tx_type=TransactionType.INTEREST.value,
            amount=75.0,
            currency="gold",
            description="Monthly interest",
        )
        for tx in (tx1, tx2, tx3):
            self._transactions.append(tx)

        # Loans
        loan1 = Loan(
            loan_id="loan_starter_01",
            borrower_id="player_starter",
            principal=50000.0,
            interest_rate=self._config.loan_interest_rate,
            term_months=12,
            remaining_principal=35000.0,
            remaining_interest=2100.0,
            status=LoanStatus.ACTIVE.value,
            disbursement_date=now - 30 * 86400,
            due_date=now + 330 * 86400,
            collateral="legendary_sword",
            payments=[
                LoanPayment(
                    payment_id="lp_01",
                    amount=15000.0,
                    principal_portion=13125.0,
                    interest_portion=1875.0,
                    timestamp=now - 15 * 86400,
                ),
            ],
        )
        loan2 = Loan(
            loan_id="loan_starter_02",
            borrower_id="player_premium",
            principal=200000.0,
            interest_rate=0.08,
            term_months=24,
            remaining_principal=200000.0,
            remaining_interest=0.0,
            status=LoanStatus.PENDING.value,
            collateral="castle_deed",
        )
        for loan in (loan1, loan2):
            self._loans[loan.loan_id] = loan

        # Safe deposit boxes
        box1 = SafeDepositBox(
            box_id="box_starter_01",
            owner_id="player_starter",
            size=BoxSize.MEDIUM.value,
            rent_paid_until=now + 2592000.0,
            contents=[
                BoxItem(
                    item_id="item_ruby_01",
                    name="Rare Ruby",
                    quantity=3,
                    rarity="rare",
                    description="A polished ruby gemstone.",
                ),
                BoxItem(
                    item_id="item_scroll_01",
                    name="Ancient Scroll",
                    quantity=1,
                    rarity="epic",
                    description="A scroll of forgotten lore.",
                ),
            ],
            access_list=[
                BoxAccessEntry(
                    player_id="player_starter",
                    player_name="Starter Player",
                    access_level=BoxAccessLevel.OWNER.value,
                    granted_by="player_starter",
                ),
            ],
        )
        box2 = SafeDepositBox(
            box_id="box_starter_02",
            owner_id="player_premium",
            size=BoxSize.LARGE.value,
            rent_paid_until=now + 5184000.0,
            contents=[
                BoxItem(
                    item_id="item_crown_01",
                    name="Royal Crown",
                    quantity=1,
                    rarity="legendary",
                    description="A crown of pure gold.",
                ),
            ],
            access_list=[
                BoxAccessEntry(
                    player_id="player_premium",
                    player_name="Premium Player",
                    access_level=BoxAccessLevel.OWNER.value,
                    granted_by="player_premium",
                ),
                BoxAccessEntry(
                    player_id="player_starter",
                    player_name="Starter Player",
                    access_level=BoxAccessLevel.GUEST.value,
                    granted_by="player_premium",
                ),
            ],
        )
        for box in (box1, box2):
            self._boxes[box.box_id] = box

        # Exchange rates
        rates = [
            ExchangeRate(from_currency="gold", to_currency="gems", rate=0.01, fee_percent=0.02),
            ExchangeRate(from_currency="gems", to_currency="gold", rate=100.0, fee_percent=0.02),
            ExchangeRate(from_currency="gold", to_currency="tokens", rate=5.0, fee_percent=0.01),
            ExchangeRate(from_currency="tokens", to_currency="gold", rate=0.2, fee_percent=0.01),
            ExchangeRate(from_currency="gems", to_currency="tokens", rate=500.0, fee_percent=0.03),
        ]
        for r in rates:
            self._exchange_rates[f"{r.from_currency}:{r.to_currency}"] = r

        # Initial events
        self._events.append(BankingEvent(
            event_id="evt_seed_01",
            event_type=BankingEventKind.ACCOUNT_OPENED.value,
            timestamp=now,
            account_id="acc_starter_01",
            description="Banking system initialized",
        ))

        self._refresh_stats()

    def _refresh_stats(self) -> None:
        self._stats.total_accounts = len(self._accounts)
        self._stats.total_balance = sum(a.balance for a in self._accounts.values() if a.status == AccountStatus.ACTIVE.value)
        self._stats.total_loans = len(self._loans)
        self._stats.total_outstanding_loan = sum(
            l.remaining_principal + l.remaining_interest
            for l in self._loans.values()
            if l.status in (LoanStatus.ACTIVE.value, LoanStatus.PENDING.value)
        )
        self._stats.total_boxes = len(self._boxes)
        self._stats.total_transactions = len(self._transactions)
        self._stats.total_deposits = sum(
            t.amount for t in self._transactions
            if t.tx_type == TransactionType.DEPOSIT.value and t.status == TransactionStatus.COMPLETED.value
        )
        self._stats.total_withdrawals = sum(
            t.amount for t in self._transactions
            if t.tx_type == TransactionType.WITHDRAWAL.value and t.status == TransactionStatus.COMPLETED.value
        )
        self._stats.total_interest_paid = sum(
            t.amount for t in self._transactions
            if t.tx_type == TransactionType.INTEREST.value and t.status == TransactionStatus.COMPLETED.value
        )
        self._stats.total_fees_collected = sum(
            t.amount for t in self._transactions
            if t.tx_type == TransactionType.FEE.value and t.status == TransactionStatus.COMPLETED.value
        )

    def _record_event(self, event_type: str, account_id: str = "", description: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        event = BankingEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            account_id=account_id,
            description=description,
            metadata=metadata or {},
        )
        self._events.append(event)
        if len(self._events) > 5000:
            self._events.pop(0)

    def _record_transaction(
        self,
        account_id: str,
        tx_type: str,
        amount: float,
        currency: str,
        description: str = "",
        related_account_id: Optional[str] = None,
        related_player_id: Optional[str] = None,
        status: str = TransactionStatus.COMPLETED.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Transaction:
        tx = Transaction(
            tx_id=_new_id("tx"),
            account_id=account_id,
            tx_type=tx_type,
            amount=amount,
            currency=currency,
            description=description,
            related_account_id=related_account_id,
            related_player_id=related_player_id,
            status=status,
            metadata=metadata or {},
        )
        self._transactions.append(tx)
        _evict_fifo_list(self._transactions, "tx_id", _MAX_TRANSACTIONS)
        return tx

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------

    def register_account(
        self,
        account_id: str,
        owner_id: str,
        account_type: str = AccountType.CHECKING.value,
        initial_balance: float = 0.0,
        currency: str = "gold",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[BankAccount]]:
        with _LOCK:
            if account_id in self._accounts:
                return False, "account_exists", None
            count = sum(1 for a in self._accounts.values() if a.owner_id == owner_id)
            if count >= self._config.max_accounts_per_player:
                return False, "max_accounts_reached", None
            rate = self._config.base_interest_rate
            if account_type == AccountType.SAVINGS.value:
                rate = self._config.savings_interest_rate
            elif account_type == AccountType.PREMIUM.value:
                rate = self._config.premium_interest_rate
            acc = BankAccount(
                account_id=account_id,
                owner_id=owner_id,
                account_type=account_type,
                balance=_safe_float(initial_balance, 0.0),
                currency=currency,
                interest_rate=rate,
                metadata=metadata or {},
            )
            self._accounts[account_id] = acc
            if acc.balance > 0:
                self._record_transaction(
                    account_id=account_id,
                    tx_type=TransactionType.DEPOSIT.value,
                    amount=acc.balance,
                    currency=currency,
                    description="Initial deposit",
                )
            self._record_event(
                BankingEventKind.ACCOUNT_OPENED.value,
                account_id=account_id,
                description=f"Account opened for {owner_id}",
            )
            self._refresh_stats()
            return True, "registered", acc

    def close_account(self, account_id: str) -> Tuple[bool, str]:
        with _LOCK:
            acc = self._accounts.get(account_id)
            if acc is None:
                return False, "account_not_found"
            if acc.status == AccountStatus.CLOSED.value:
                return False, "already_closed"
            if acc.balance > 0:
                return False, "balance_outstanding"
            acc.status = AccountStatus.CLOSED.value
            self._record_event(
                BankingEventKind.ACCOUNT_CLOSED.value,
                account_id=account_id,
                description=f"Account closed",
            )
            self._refresh_stats()
            return True, "closed"

    def freeze_account(self, account_id: str, frozen: bool = True) -> Tuple[bool, str]:
        with _LOCK:
            acc = self._accounts.get(account_id)
            if acc is None:
                return False, "account_not_found"
            if acc.status == AccountStatus.CLOSED.value:
                return False, "account_closed"
            acc.status = AccountStatus.FROZEN.value if frozen else AccountStatus.ACTIVE.value
            self._record_event(
                BankingEventKind.ACCOUNT_FROZEN.value,
                account_id=account_id,
                description=f"Account {'frozen' if frozen else 'unfrozen'}",
            )
            return True, "frozen" if frozen else "unfrozen"

    def get_account(self, account_id: str) -> Optional[BankAccount]:
        with _LOCK:
            return self._accounts.get(account_id)

    def list_accounts(
        self,
        owner_id: Optional[str] = None,
        account_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[BankAccount]:
        with _LOCK:
            results = []
            for acc in self._accounts.values():
                if owner_id is not None and acc.owner_id != owner_id:
                    continue
                if account_type is not None and acc.account_type != account_type:
                    continue
                if status is not None and acc.status != status:
                    continue
                results.append(acc)
            return results

    # ------------------------------------------------------------------
    # Deposits and withdrawals
    # ------------------------------------------------------------------

    def deposit(
        self,
        account_id: str,
        amount: float,
        description: str = "",
        currency: str = "gold",
    ) -> Tuple[bool, str, Optional[Transaction]]:
        with _LOCK:
            acc = self._accounts.get(account_id)
            if acc is None:
                return False, "account_not_found", None
            if acc.status != AccountStatus.ACTIVE.value:
                return False, "account_not_active", None
            amt = _safe_float(amount, 0.0)
            if amt <= 0:
                return False, "invalid_amount", None
            acc.balance += amt
            tx = self._record_transaction(
                account_id=account_id,
                tx_type=TransactionType.DEPOSIT.value,
                amount=amt,
                currency=currency,
                description=description or "Deposit",
            )
            self._record_event(
                BankingEventKind.DEPOSIT.value,
                account_id=account_id,
                description=f"Deposited {amt} {currency}",
            )
            self._refresh_stats()
            return True, "deposited", tx

    def withdraw(
        self,
        account_id: str,
        amount: float,
        description: str = "",
        currency: str = "gold",
    ) -> Tuple[bool, str, Optional[Transaction]]:
        with _LOCK:
            acc = self._accounts.get(account_id)
            if acc is None:
                return False, "account_not_found", None
            if acc.status != AccountStatus.ACTIVE.value:
                return False, "account_not_active", None
            amt = _safe_float(amount, 0.0)
            if amt <= 0:
                return False, "invalid_amount", None
            if acc.balance < amt:
                return False, "insufficient_funds", None
            acc.balance -= amt
            tx = self._record_transaction(
                account_id=account_id,
                tx_type=TransactionType.WITHDRAWAL.value,
                amount=amt,
                currency=currency,
                description=description or "Withdrawal",
            )
            self._record_event(
                BankingEventKind.WITHDRAWAL.value,
                account_id=account_id,
                description=f"Withdrew {amt} {currency}",
            )
            self._refresh_stats()
            return True, "withdrawn", tx

    def transfer(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        description: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with _LOCK:
            src = self._accounts.get(from_account_id)
            dst = self._accounts.get(to_account_id)
            if src is None:
                return False, "source_not_found", None
            if dst is None:
                return False, "destination_not_found", None
            if src.status != AccountStatus.ACTIVE.value:
                return False, "source_not_active", None
            if dst.status != AccountStatus.ACTIVE.value:
                return False, "destination_not_active", None
            amt = _safe_float(amount, 0.0)
            if amt <= 0:
                return False, "invalid_amount", None
            fee = amt * self._config.transfer_fee_percent
            total = amt + fee
            if src.balance < total:
                return False, "insufficient_funds", None
            src.balance -= total
            dst.balance += amt
            tx_out = self._record_transaction(
                account_id=from_account_id,
                tx_type=TransactionType.TRANSFER_OUT.value,
                amount=amt,
                currency=src.currency,
                description=description or f"Transfer to {to_account_id}",
                related_account_id=to_account_id,
            )
            tx_in = self._record_transaction(
                account_id=to_account_id,
                tx_type=TransactionType.TRANSFER_IN.value,
                amount=amt,
                currency=dst.currency,
                description=description or f"Transfer from {from_account_id}",
                related_account_id=from_account_id,
            )
            if fee > 0:
                self._record_transaction(
                    account_id=from_account_id,
                    tx_type=TransactionType.FEE.value,
                    amount=fee,
                    currency=src.currency,
                    description="Transfer fee",
                )
            self._record_event(
                BankingEventKind.TRANSFER.value,
                account_id=from_account_id,
                description=f"Transferred {amt} to {to_account_id}",
            )
            self._refresh_stats()
            return True, "transferred", {"outgoing": tx_out.to_dict(), "incoming": tx_in.to_dict(), "fee": fee}

    # ------------------------------------------------------------------
    # Interest
    # ------------------------------------------------------------------

    def accrue_interest(self, account_id: str) -> Tuple[bool, str, float]:
        with _LOCK:
            acc = self._accounts.get(account_id)
            if acc is None:
                return False, "account_not_found", 0.0
            if acc.status != AccountStatus.ACTIVE.value:
                return False, "account_not_active", 0.0
            now = _now()
            elapsed = now - acc.last_interest_at
            if elapsed <= 0:
                return False, "no_time_elapsed", 0.0
            # Simple interest: rate * elapsed / month (30 days)
            month_seconds = 30 * 86400
            interest = acc.balance * acc.interest_rate * (elapsed / month_seconds)
            if interest <= 0:
                return False, "no_interest", 0.0
            acc.balance += interest
            acc.last_interest_at = now
            self._record_transaction(
                account_id=account_id,
                tx_type=TransactionType.INTEREST.value,
                amount=interest,
                currency=acc.currency,
                description="Interest accrual",
            )
            self._record_event(
                BankingEventKind.INTEREST_ACCRUED.value,
                account_id=account_id,
                description=f"Interest {interest} {acc.currency}",
            )
            self._refresh_stats()
            return True, "accrued", interest

    def accrue_all_interest(self) -> Dict[str, Any]:
        with _LOCK:
            results: Dict[str, Any] = {}
            total_interest = 0.0
            for acc_id in list(self._accounts.keys()):
                ok, msg, interest = self.accrue_interest(acc_id)
                results[acc_id] = {"ok": ok, "message": msg, "interest": interest}
                if ok:
                    total_interest += interest
            return {"accounts": results, "total_interest": total_interest}

    # ------------------------------------------------------------------
    # Loans
    # ------------------------------------------------------------------

    def request_loan(
        self,
        loan_id: str,
        borrower_id: str,
        principal: float,
        term_months: int = 12,
        collateral: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Loan]]:
        with _LOCK:
            if loan_id in self._loans:
                return False, "loan_exists", None
            principal_val = _safe_float(principal, 0.0)
            if principal_val <= 0:
                return False, "invalid_principal", None
            if principal_val > self._config.max_loan_amount:
                return False, "exceeds_max_loan", None
            term = _safe_int(term_months, 12)
            if term <= 0:
                return False, "invalid_term", None
            loan = Loan(
                loan_id=loan_id,
                borrower_id=borrower_id,
                principal=principal_val,
                interest_rate=self._config.loan_interest_rate,
                term_months=term,
                remaining_principal=principal_val,
                remaining_interest=principal_val * self._config.loan_interest_rate * (term / 12.0),
                status=LoanStatus.PENDING.value,
                collateral=collateral,
                metadata=metadata or {},
            )
            self._loans[loan_id] = loan
            self._record_event(
                BankingEventKind.LOAN_REQUESTED.value,
                description=f"Loan {loan_id} requested by {borrower_id}",
            )
            self._refresh_stats()
            return True, "requested", loan

    def approve_loan(self, loan_id: str, disbursement_account_id: str) -> Tuple[bool, str, Optional[Loan]]:
        with _LOCK:
            loan = self._loans.get(loan_id)
            if loan is None:
                return False, "loan_not_found", None
            if loan.status != LoanStatus.PENDING.value:
                return False, "loan_not_pending", None
            acc = self._accounts.get(disbursement_account_id)
            if acc is None:
                return False, "account_not_found", None
            now = _now()
            loan.status = LoanStatus.ACTIVE.value
            loan.disbursement_date = now
            loan.due_date = now + loan.term_months * 30 * 86400
            acc.balance += loan.principal
            self._record_transaction(
                account_id=disbursement_account_id,
                tx_type=TransactionType.LOAN_DISBURSEMENT.value,
                amount=loan.principal,
                currency=acc.currency,
                description=f"Loan {loan_id} disbursed",
                metadata={"loan_id": loan_id},
            )
            self._record_event(
                BankingEventKind.LOAN_APPROVED.value,
                account_id=disbursement_account_id,
                description=f"Loan {loan_id} approved",
            )
            self._refresh_stats()
            return True, "approved", loan

    def reject_loan(self, loan_id: str) -> Tuple[bool, str]:
        with _LOCK:
            loan = self._loans.get(loan_id)
            if loan is None:
                return False, "loan_not_found"
            if loan.status != LoanStatus.PENDING.value:
                return False, "loan_not_pending"
            loan.status = LoanStatus.CANCELLED.value
            self._record_event(
                BankingEventKind.LOAN_REJECTED.value,
                description=f"Loan {loan_id} rejected",
            )
            self._refresh_stats()
            return True, "rejected"

    def repay_loan(self, loan_id: str, amount: float, from_account_id: str) -> Tuple[bool, str, Optional[LoanPayment]]:
        with _LOCK:
            loan = self._loans.get(loan_id)
            if loan is None:
                return False, "loan_not_found", None
            if loan.status != LoanStatus.ACTIVE.value:
                return False, "loan_not_active", None
            acc = self._accounts.get(from_account_id)
            if acc is None:
                return False, "account_not_found", None
            if acc.status != AccountStatus.ACTIVE.value:
                return False, "account_not_active", None
            amt = _safe_float(amount, 0.0)
            if amt <= 0:
                return False, "invalid_amount", None
            if acc.balance < amt:
                return False, "insufficient_funds", None
            # Apply payment to interest first, then principal
            interest_portion = min(amt, loan.remaining_interest)
            principal_portion = amt - interest_portion
            principal_portion = min(principal_portion, loan.remaining_principal)
            acc.balance -= amt
            loan.remaining_interest -= interest_portion
            loan.remaining_principal -= principal_portion
            payment = LoanPayment(
                payment_id=_new_id("lp"),
                amount=amt,
                principal_portion=principal_portion,
                interest_portion=interest_portion,
                timestamp=_now(),
            )
            loan.payments.append(payment)
            self._record_transaction(
                account_id=from_account_id,
                tx_type=TransactionType.LOAN_REPAYMENT.value,
                amount=amt,
                currency=acc.currency,
                description=f"Loan {loan_id} repayment",
                metadata={"loan_id": loan_id, "payment_id": payment.payment_id},
            )
            if loan.remaining_principal <= 0 and loan.remaining_interest <= 0:
                loan.status = LoanStatus.PAID_OFF.value
                self._record_event(
                    BankingEventKind.LOAN_REPAID.value,
                    description=f"Loan {loan_id} paid off",
                )
            self._refresh_stats()
            return True, "repaid", payment

    def default_loan(self, loan_id: str) -> Tuple[bool, str]:
        with _LOCK:
            loan = self._loans.get(loan_id)
            if loan is None:
                return False, "loan_not_found"
            if loan.status != LoanStatus.ACTIVE.value:
                return False, "loan_not_active"
            loan.status = LoanStatus.DEFAULTED.value
            self._record_event(
                BankingEventKind.LOAN_DEFAULTED.value,
                description=f"Loan {loan_id} defaulted",
            )
            self._refresh_stats()
            return True, "defaulted"

    def get_loan(self, loan_id: str) -> Optional[Loan]:
        with _LOCK:
            return self._loans.get(loan_id)

    def list_loans(
        self,
        borrower_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Loan]:
        with _LOCK:
            results = []
            for loan in self._loans.values():
                if borrower_id is not None and loan.borrower_id != borrower_id:
                    continue
                if status is not None and loan.status != status:
                    continue
                results.append(loan)
            return results

    # ------------------------------------------------------------------
    # Safe deposit boxes
    # ------------------------------------------------------------------

    def rent_box(
        self,
        box_id: str,
        owner_id: str,
        size: str = BoxSize.SMALL.value,
        owner_name: str = "",
        duration: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[SafeDepositBox]]:
        with _LOCK:
            if box_id in self._boxes:
                return False, "box_exists", None
            rent_map = {
                BoxSize.SMALL.value: self._config.box_rent_small,
                BoxSize.MEDIUM.value: self._config.box_rent_medium,
                BoxSize.LARGE.value: self._config.box_rent_large,
                BoxSize.HUGE.value: self._config.box_rent_huge,
            }
            if size not in rent_map:
                return False, "invalid_size", None
            dur = duration if duration is not None else self._config.box_rent_duration
            now = _now()
            box = SafeDepositBox(
                box_id=box_id,
                owner_id=owner_id,
                size=size,
                rent_paid_until=now + dur,
                access_list=[
                    BoxAccessEntry(
                        player_id=owner_id,
                        player_name=owner_name or owner_id,
                        access_level=BoxAccessLevel.OWNER.value,
                        granted_by=owner_id,
                    ),
                ],
            )
            self._boxes[box_id] = box
            self._record_event(
                BankingEventKind.BOX_RENTED.value,
                description=f"Box {box_id} rented by {owner_id}",
                metadata={"box_id": box_id, "size": size, "rent": rent_map[size]},
            )
            self._refresh_stats()
            return True, "rented", box

    def open_box(self, box_id: str, opener_id: str) -> Tuple[bool, str, Optional[SafeDepositBox]]:
        with _LOCK:
            box = self._boxes.get(box_id)
            if box is None:
                return False, "box_not_found", None
            now = _now()
            if box.rent_paid_until < now:
                return False, "rent_expired", None
            access = next((a for a in box.access_list if a.player_id == opener_id), None)
            if access is None:
                return False, "access_denied", None
            self._record_event(
                BankingEventKind.BOX_OPENED.value,
                description=f"Box {box_id} opened by {opener_id}",
            )
            return True, "opened", box

    def close_box(self, box_id: str) -> Tuple[bool, str]:
        with _LOCK:
            box = self._boxes.get(box_id)
            if box is None:
                return False, "box_not_found"
            self._record_event(
                BankingEventKind.BOX_CLOSED.value,
                description=f"Box {box_id} closed",
            )
            return True, "closed"

    def renew_box(self, box_id: str, duration: Optional[float] = None) -> Tuple[bool, str, Optional[SafeDepositBox]]:
        with _LOCK:
            box = self._boxes.get(box_id)
            if box is None:
                return False, "box_not_found", None
            dur = duration if duration is not None else self._config.box_rent_duration
            now = _now()
            base = max(box.rent_paid_until, now)
            box.rent_paid_until = base + dur
            return True, "renewed", box

    def store_item(
        self,
        box_id: str,
        item_id: str,
        name: str,
        quantity: int = 1,
        rarity: str = "common",
        description: str = "",
    ) -> Tuple[bool, str, Optional[BoxItem]]:
        with _LOCK:
            box = self._boxes.get(box_id)
            if box is None:
                return False, "box_not_found", None
            if len(box.contents) >= _MAX_BOX_ITEMS:
                return False, "box_full", None
            qty = _safe_int(quantity, 1)
            if qty <= 0:
                return False, "invalid_quantity", None
            # If item already exists, stack it
            existing = next((c for c in box.contents if c.item_id == item_id), None)
            if existing:
                existing.quantity += qty
                self._record_event(
                    BankingEventKind.ITEM_STORED.value,
                    description=f"Stacked {qty}x {name} into box {box_id}",
                )
                return True, "stacked", existing
            item = BoxItem(
                item_id=item_id,
                name=name,
                quantity=qty,
                rarity=rarity,
                description=description,
            )
            box.contents.append(item)
            self._record_event(
                BankingEventKind.ITEM_STORED.value,
                description=f"Stored {qty}x {name} into box {box_id}",
            )
            return True, "stored", item

    def retrieve_item(self, box_id: str, item_id: str, quantity: int = 1) -> Tuple[bool, str, Optional[BoxItem]]:
        with _LOCK:
            box = self._boxes.get(box_id)
            if box is None:
                return False, "box_not_found", None
            item = next((c for c in box.contents if c.item_id == item_id), None)
            if item is None:
                return False, "item_not_found", None
            qty = _safe_int(quantity, 1)
            if qty <= 0:
                return False, "invalid_quantity", None
            if item.quantity < qty:
                return False, "insufficient_quantity", None
            item.quantity -= qty
            retrieved = BoxItem(
                item_id=item.item_id,
                name=item.name,
                quantity=qty,
                rarity=item.rarity,
                description=item.description,
            )
            if item.quantity <= 0:
                box.contents.remove(item)
            self._record_event(
                BankingEventKind.ITEM_RETRIEVED.value,
                description=f"Retrieved {qty}x {item.name} from box {box_id}",
            )
            return True, "retrieved", retrieved

    def get_box(self, box_id: str) -> Optional[SafeDepositBox]:
        with _LOCK:
            return self._boxes.get(box_id)

    def list_boxes(
        self,
        owner_id: Optional[str] = None,
        size: Optional[str] = None,
    ) -> List[SafeDepositBox]:
        with _LOCK:
            results = []
            for box in self._boxes.values():
                if owner_id is not None and box.owner_id != owner_id:
                    continue
                if size is not None and box.size != size:
                    continue
                results.append(box)
            return results

    def add_box_access(
        self,
        box_id: str,
        player_id: str,
        player_name: str,
        access_level: str = BoxAccessLevel.GUEST.value,
        granted_by: str = "",
    ) -> Tuple[bool, str, Optional[BoxAccessEntry]]:
        with _LOCK:
            box = self._boxes.get(box_id)
            if box is None:
                return False, "box_not_found", None
            existing = next((a for a in box.access_list if a.player_id == player_id), None)
            if existing:
                existing.access_level = access_level
                return True, "updated", existing
            entry = BoxAccessEntry(
                player_id=player_id,
                player_name=player_name,
                access_level=access_level,
                granted_by=granted_by,
            )
            box.access_list.append(entry)
            return True, "added", entry

    def remove_box_access(self, box_id: str, player_id: str) -> Tuple[bool, str]:
        with _LOCK:
            box = self._boxes.get(box_id)
            if box is None:
                return False, "box_not_found"
            entry = next((a for a in box.access_list if a.player_id == player_id), None)
            if entry is None:
                return False, "access_not_found"
            if entry.access_level == BoxAccessLevel.OWNER.value:
                return False, "cannot_remove_owner"
            box.access_list.remove(entry)
            return True, "removed"

    # ------------------------------------------------------------------
    # Currency exchange
    # ------------------------------------------------------------------

    def set_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        fee_percent: float = 0.0,
    ) -> Tuple[bool, str, Optional[ExchangeRate]]:
        with _LOCK:
            if rate <= 0:
                return False, "invalid_rate", None
            key = f"{from_currency}:{to_currency}"
            er = ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                fee_percent=fee_percent,
            )
            self._exchange_rates[key] = er
            return True, "set", er

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        with _LOCK:
            return self._exchange_rates.get(f"{from_currency}:{to_currency}")

    def list_exchange_rates(self) -> List[ExchangeRate]:
        with _LOCK:
            return list(self._exchange_rates.values())

    def exchange_currency(
        self,
        account_id: str,
        from_currency: str,
        to_currency: str,
        amount: float,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        with _LOCK:
            acc = self._accounts.get(account_id)
            if acc is None:
                return False, "account_not_found", None
            if acc.status != AccountStatus.ACTIVE.value:
                return False, "account_not_active", None
            er = self._exchange_rates.get(f"{from_currency}:{to_currency}")
            if er is None:
                return False, "rate_not_found", None
            amt = _safe_float(amount, 0.0)
            if amt <= 0:
                return False, "invalid_amount", None
            # We only debit if account currency matches from_currency
            if acc.currency != from_currency:
                return False, "currency_mismatch", None
            if acc.balance < amt:
                return False, "insufficient_funds", None
            fee = amt * er.fee_percent
            converted = (amt - fee) * er.rate
            acc.balance -= amt
            self._record_transaction(
                account_id=account_id,
                tx_type=TransactionType.EXCHANGE_OUT.value,
                amount=amt,
                currency=from_currency,
                description=f"Exchange {amt} {from_currency} -> {to_currency}",
                metadata={"rate": er.rate, "fee": fee},
            )
            self._record_transaction(
                account_id=account_id,
                tx_type=TransactionType.EXCHANGE_IN.value,
                amount=converted,
                currency=to_currency,
                description=f"Exchange received {converted} {to_currency}",
                metadata={"rate": er.rate, "fee": fee},
            )
            self._record_event(
                BankingEventKind.EXCHANGE.value,
                account_id=account_id,
                description=f"Exchanged {amt} {from_currency} -> {converted} {to_currency}",
            )
            self._refresh_stats()
            return True, "exchanged", {
                "from_amount": amt,
                "from_currency": from_currency,
                "to_amount": converted,
                "to_currency": to_currency,
                "rate": er.rate,
                "fee": fee,
            }

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        with _LOCK:
            for tx in self._transactions:
                if tx.tx_id == tx_id:
                    return tx
            return None

    def list_transactions(
        self,
        account_id: Optional[str] = None,
        tx_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Transaction]:
        with _LOCK:
            results = []
            lim = _safe_int(limit, 100)
            if lim <= 0:
                lim = 100
            for tx in reversed(self._transactions):
                if account_id is not None and tx.account_id != account_id:
                    continue
                if tx_type is not None and tx.tx_type != tx_type:
                    continue
                if status is not None and tx.status != status:
                    continue
                results.append(tx)
                if len(results) >= lim:
                    break
            return results

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            now = _now()
            # Check for overdue loans
            defaulted = []
            for loan in self._loans.values():
                if loan.status == LoanStatus.ACTIVE.value and loan.due_date is not None and loan.due_date < now:
                    loan.status = LoanStatus.DEFAULTED.value
                    defaulted.append(loan.loan_id)
                    self._record_event(
                        BankingEventKind.LOAN_DEFAULTED.value,
                        description=f"Loan {loan.loan_id} auto-defaulted (overdue)",
                    )
            # Check for expired box rentals
            expired_boxes = []
            for box in self._boxes.values():
                if box.rent_paid_until < now:
                    expired_boxes.append(box.box_id)
            self._refresh_stats()
            return {
                "tick_count": self._tick_count,
                "defaulted_loans": defaulted,
                "expired_boxes": expired_boxes,
            }

    # ------------------------------------------------------------------
    # Config, stats, status, snapshot
    # ------------------------------------------------------------------

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, Optional[BankingConfig]]:
        with _LOCK:
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
            self._record_event(
                BankingEventKind.CONFIG_UPDATED.value,
                description="Configuration updated",
            )
            return True, "updated", self._config

    def get_config(self) -> BankingConfig:
        with _LOCK:
            return self._config

    def list_events(
        self,
        account_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[BankingEvent]:
        with _LOCK:
            results = []
            lim = _safe_int(limit, 100)
            if lim <= 0:
                lim = 100
            for evt in reversed(self._events):
                if account_id is not None and evt.account_id != account_id:
                    continue
                if event_type is not None and evt.event_type != event_type:
                    continue
                results.append(evt)
                if len(results) >= lim:
                    break
            return results

    def get_stats(self) -> BankingStats:
        with _LOCK:
            self._refresh_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            return {
                "initialized": self._initialized,
                "total_accounts": len(self._accounts),
                "total_loans": len(self._loans),
                "total_boxes": len(self._boxes),
                "total_transactions": len(self._transactions),
                "total_exchange_rates": len(self._exchange_rates),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> BankingSnapshot:
        with _LOCK:
            self._refresh_stats()
            return BankingSnapshot(
                config=self._config,
                stats=self._stats,
                accounts=list(self._accounts.values()),
                transactions=list(self._transactions[-200:]),
                loans=list(self._loans.values()),
                boxes=list(self._boxes.values()),
                exchange_rates=list(self._exchange_rates.values()),
            )

    def reset(self) -> Dict[str, Any]:
        with _LOCK:
            self._config = BankingConfig()
            self._stats = BankingStats()
            self._accounts.clear()
            self._transactions.clear()
            self._loans.clear()
            self._boxes.clear()
            self._exchange_rates.clear()
            self._events.clear()
            self._tick_count = 0
            self._initialized = False
            self._seed()
            self._initialized = True
            self._record_event(
                BankingEventKind.RESET.value,
                description="Banking system reset",
            )
            return self.get_status()


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

def get_banking_vault_system() -> BankingVaultSystem:
    return BankingVaultSystem()
