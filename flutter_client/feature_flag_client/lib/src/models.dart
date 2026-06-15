import 'dart:convert';
import 'package:crypto/crypto.dart';

/// Describes WHO a feature flag is enabled for.
///
/// - `everyone`   -> the flag applies to all users
/// - `beta_only`  -> the flag only applies to user IDs in [betaUserIds]
/// - `percentage` -> the flag applies to a consistent percentage of users
class RolloutRule {
  final String type;
  final int percentage;
  final List<String> betaUserIds;

  RolloutRule({
    required this.type,
    required this.percentage,
    required this.betaUserIds,
  });

  factory RolloutRule.fromJson(Map<String, dynamic> json) {
    return RolloutRule(
      type: json['type'] as String,
      percentage: json['percentage'] as int,
      betaUserIds: List<String>.from(json['beta_user_ids'] as List),
    );
  }
}

/// A single on/off feature flag plus its targeting rule.
class FeatureFlag {
  final String name;
  final bool enabled;
  final RolloutRule rollout;

  FeatureFlag({
    required this.name,
    required this.enabled,
    required this.rollout,
  });

  factory FeatureFlag.fromJson(Map<String, dynamic> json) {
    return FeatureFlag(
      name: json['name'] as String,
      enabled: json['enabled'] as bool,
      rollout: RolloutRule.fromJson(json['rollout'] as Map<String, dynamic>),
    );
  }

  /// Evaluate whether this flag should be ON for [userId].
  ///
  /// This mirrors `evaluation.py` on the server byte-for-byte, so a given
  /// user always lands in the same bucket whether the decision is made
  /// here on the device or on the backend.
  bool isEnabledFor(String? userId) {
    if (!enabled) return false;

    switch (rollout.type) {
      case 'everyone':
        return true;
      case 'beta_only':
        return userId != null && rollout.betaUserIds.contains(userId);
      case 'percentage':
        if (userId == null) return false;
        return _bucketForUser(name, userId) < rollout.percentage;
      default:
        return false;
    }
  }

  /// Deterministically maps (flagName, userId) to a number 0-99.
  /// Matches Python's `int(md5_hexdigest, 16) % 100`.
  static int _bucketForUser(String flagName, String userId) {
    final digestHex = md5.convert(utf8.encode('$flagName:$userId')).toString();
    final bigInt = BigInt.parse(digestHex, radix: 16);
    return (bigInt % BigInt.from(100)).toInt();
  }
}

/// A single remote config value (a "string" or a "number").
class RemoteConfig {
  final String key;
  final dynamic value;
  final String valueType;

  RemoteConfig({
    required this.key,
    required this.value,
    required this.valueType,
  });

  factory RemoteConfig.fromJson(Map<String, dynamic> json) {
    return RemoteConfig(
      key: json['key'] as String,
      value: json['value'],
      valueType: json['value_type'] as String,
    );
  }

  String asString() => value.toString();

  num asNumber() => value as num;
}
