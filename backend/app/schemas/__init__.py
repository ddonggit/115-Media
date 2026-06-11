"""Pydantic v2 schemas — auto-generated from SQLAlchemy models."""
from .account import Account115Create, Account115Update, Account115Response
from .subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    MediaType,
    Quality,
    UpgradeStrategy,
    SubStatus,
)
from .rss_source import RSSSourceCreate, RSSSourceUpdate, RSSSourceResponse
from .transfer_task import (
    TransferTaskCreate,
    TransferTaskUpdate,
    TransferTaskResponse,
    TransferStatus,
)
from .sync_record import SyncRecordCreate, SyncRecordUpdate, SyncRecordResponse
from .media_file import MediaFileCreate, MediaFileUpdate, MediaFileResponse
from .organize_rule import OrganizeRuleCreate, OrganizeRuleUpdate, OrganizeRuleResponse
from .organize_config import OrganizeConfigCreate, OrganizeConfigUpdate, OrganizeConfigResponse
from .error_log import ErrorLogCreate, ErrorLogUpdate, ErrorLogResponse
from .operation_log import OperationLogCreate, OperationLogResponse
from .strm_config import StrmConfigCreate, StrmConfigUpdate, StrmConfigResponse
from .tmdb_config import TmdbConfigCreate, TmdbConfigUpdate, TmdbConfigResponse
from .notify_config import NotifyConfigCreate, NotifyConfigUpdate, NotifyConfigResponse
from .transfer_config import TransferConfigCreate, TransferConfigUpdate, TransferConfigResponse
from .subscription_config import SubscriptionConfigCreate, SubscriptionConfigUpdate, SubscriptionConfigResponse
from .sync_config import SyncConfigCreate, SyncConfigUpdate, SyncConfigResponse

__all__ = [
    "Account115Create", "Account115Update", "Account115Response",
    "SubscriptionCreate", "SubscriptionUpdate", "SubscriptionResponse",
    "MediaType", "Quality", "UpgradeStrategy", "SubStatus",
    "RSSSourceCreate", "RSSSourceUpdate", "RSSSourceResponse",
    "TransferTaskCreate", "TransferTaskUpdate", "TransferTaskResponse",
    "TransferStatus",
    "SyncRecordCreate", "SyncRecordUpdate", "SyncRecordResponse",
    "MediaFileCreate", "MediaFileUpdate", "MediaFileResponse",
    "OrganizeRuleCreate", "OrganizeRuleUpdate", "OrganizeRuleResponse",
    "OrganizeConfigCreate", "OrganizeConfigUpdate", "OrganizeConfigResponse",
    "ErrorLogCreate", "ErrorLogUpdate", "ErrorLogResponse",
    "OperationLogCreate", "OperationLogResponse",
    "StrmConfigCreate", "StrmConfigUpdate", "StrmConfigResponse",
    "TmdbConfigCreate", "TmdbConfigUpdate", "TmdbConfigResponse",
    "NotifyConfigCreate", "NotifyConfigUpdate", "NotifyConfigResponse",
    "TransferConfigCreate", "TransferConfigUpdate", "TransferConfigResponse",
    "SubscriptionConfigCreate", "SubscriptionConfigUpdate", "SubscriptionConfigResponse",
    "SyncConfigCreate", "SyncConfigUpdate", "SyncConfigResponse",
]
