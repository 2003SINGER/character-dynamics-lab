#pragma once
namespace RuntimeConfig {
inline constexpr double NeedReconsiderationThreshold = 0.40;
inline constexpr int RejectionFeedbackLatencyMinutes = 1;
inline constexpr int PhysicalInvalidationLatencyMinutes = 1;
inline constexpr int DefaultMaxIntegrationStepMinutes = 60;
inline constexpr unsigned int DefaultPolicySeed = 0x43445257U;
}
