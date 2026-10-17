//! Stable domain outcomes. Diagnostics never decide retry or fallback policy.
use serde::{Deserialize, Serialize};
use std::fmt;
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    ParametersUnavailable,
    InvalidParameters,
    ProfileFormatMismatch,
    WorkerProfileMismatch,
    UnsupportedZkirVersion,
    InvalidInput,
    IntegrityError,
    ArtifactIdentityChanged,
    NotFound,
    ArtifactsUnavailable,
    Unauthorized,
    Busy,
    InternalError,
    ProviderLimit,
    ProviderStorageUnavailable,
    SnapshotDestinationExists,
    SnapshotProfileMismatch,
    SnapshotPartitionMismatch,
    SnapshotSchemaMismatch,
    SnapshotUnsafePath,
    SnapshotLimit,
    SnapshotBusy,
    SnapshotPublishFailed,
}
impl Kind {
    pub fn code(self) -> &'static str {
        match self {
            Self::ParametersUnavailable => "parameters_unavailable",
            Self::InvalidParameters => "invalid_parameters",
            Self::ProfileFormatMismatch => "profile_format_mismatch",
            Self::WorkerProfileMismatch => "worker_profile_mismatch",
            Self::UnsupportedZkirVersion => "unsupported_zkir_version",
            Self::InvalidInput => "invalid_input",
            Self::IntegrityError => "integrity_error",
            Self::ArtifactIdentityChanged => "artifact_identity_changed",
            Self::NotFound => "not_found",
            Self::ArtifactsUnavailable => "artifacts_unavailable",
            Self::Unauthorized => "unauthorized",
            Self::Busy => "busy",
            Self::InternalError => "internal_error",
            Self::ProviderLimit => "provider_limit",
            Self::ProviderStorageUnavailable => "provider_storage_unavailable",
            Self::SnapshotDestinationExists => "snapshot_destination_exists",
            Self::SnapshotProfileMismatch => "snapshot_profile_mismatch",
            Self::SnapshotPartitionMismatch => "snapshot_partition_mismatch",
            Self::SnapshotSchemaMismatch => "snapshot_schema_mismatch",
            Self::SnapshotUnsafePath => "snapshot_unsafe_path",
            Self::SnapshotLimit => "snapshot_limit",
            Self::SnapshotBusy => "snapshot_busy",
            Self::SnapshotPublishFailed => "snapshot_publish_failed",
        }
    }
    pub fn status(self) -> u16 {
        match self {
            Self::ParametersUnavailable => 503,
            Self::InvalidParameters => 422,
            Self::ProfileFormatMismatch
            | Self::WorkerProfileMismatch
            | Self::IntegrityError
            | Self::ArtifactIdentityChanged
            | Self::SnapshotDestinationExists
            | Self::SnapshotProfileMismatch
            | Self::SnapshotPartitionMismatch
            | Self::SnapshotSchemaMismatch => 409,
            Self::UnsupportedZkirVersion
            | Self::InvalidInput
            | Self::SnapshotUnsafePath
            | Self::SnapshotLimit
            | Self::ProviderLimit => 400,
            Self::ProviderStorageUnavailable => 507,
            Self::NotFound | Self::ArtifactsUnavailable => 404,
            Self::Unauthorized => 401,
            Self::Busy | Self::SnapshotBusy => 429,
            Self::InternalError | Self::SnapshotPublishFailed => 500,
        }
    }
    pub fn availability_fallback(self) -> bool {
        matches!(
            self,
            Self::ParametersUnavailable
                | Self::NotFound
                | Self::ArtifactsUnavailable
                | Self::Busy
                | Self::SnapshotBusy
        )
    }
    pub fn retryable(self) -> bool {
        matches!(
            self,
            Self::ParametersUnavailable | Self::Busy | Self::SnapshotBusy
        )
    }
}
impl fmt::Display for Kind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}
impl std::error::Error for Kind {}
pub fn classify(error: &anyhow::Error) -> Kind {
    if let Some(kind) = error.downcast_ref::<Kind>() {
        return *kind;
    }
    // SQLite exposes typed lock contention; arbitrary I/O failures are not cache misses.
    Kind::InternalError
}
#[macro_export]
macro_rules! require {
    ($condition:expr, $kind:expr, $($message:tt)+) => {
        if !$condition {return Err(anyhow::anyhow!($($message)+).context($kind));}
    };
}
