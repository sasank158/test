import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import 'models.dart';

/// A real-time client for the self-hosted Feature Flag & Remote Config Engine.
///
/// On [connect], it fetches the current state once over HTTP, then opens a
/// WebSocket connection that pushes the full state again every time an admin
/// changes something in the terminal dashboard (or via the API). Any time
/// new data arrives, the [updates] stream fires so your widgets can rebuild.
class FeatureFlagClient {
  /// Base URL of the backend, e.g. `http://192.168.1.50:8000`.
  ///
  /// - On a physical device, use your computer's LAN IP address.
  /// - On the Android emulator, use `http://10.0.2.2:8000`.
  /// - On the iOS simulator or desktop/web, `http://localhost:8000` works.
  final String baseUrl;

  /// The ID of the current user. Used to evaluate "beta_only" and
  /// "percentage" rollout rules. Pass `null` if the app has no concept
  /// of a logged-in user (flags will then only apply if their rule is
  /// "everyone").
  String? _userId;

  String? get userId => _userId;

  set userId(String? value) {
    if (_userId != value) {
      _userId = value;
      if (!_updatesController.isClosed) {
        _updatesController.add(null);
      }
    }
  }

  Map<String, FeatureFlag> _flags = {};
  Map<String, RemoteConfig> _configs = {};

  WebSocketChannel? _channel;
  bool _disposed = false;
  final StreamController<void> _updatesController = StreamController<void>.broadcast();

  FeatureFlagClient({required this.baseUrl, String? userId}) : _userId = userId;

  /// Fires every time fresh data arrives from the server (initial load and
  /// every subsequent live update). Listen to this and call `setState`.
  Stream<void> get updates => _updatesController.stream;

  /// Fetches the current state once and opens a live WebSocket connection.
  Future<void> connect() async {
    await _fetchInitialState();
    _connectWebSocket();
  }

  Future<void> _fetchInitialState() async {
    final response = await http.get(Uri.parse('$baseUrl/api/state'));
    if (response.statusCode == 200) {
      _applyState(jsonDecode(response.body) as Map<String, dynamic>);
    } else {
      throw Exception('Failed to load feature flag state (${response.statusCode})');
    }
  }

  void _connectWebSocket() {
    if (_disposed) return;

    final wsUrl = baseUrl.replaceFirst(RegExp(r'^http'), 'ws') + '/ws';
    final channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    _channel = channel;

    channel.stream.listen(
      (message) {
        _applyState(jsonDecode(message as String) as Map<String, dynamic>);
      },
      onDone: _scheduleReconnect,
      onError: (_) => _scheduleReconnect(),
    );
  }

  void _scheduleReconnect() {
    if (_disposed) return;
    Future.delayed(const Duration(seconds: 3), _connectWebSocket);
  }

  void _applyState(Map<String, dynamic> state) {
    final flagList = (state['flags'] as List)
        .map((f) => FeatureFlag.fromJson(f as Map<String, dynamic>));
    final configList = (state['configs'] as List)
        .map((c) => RemoteConfig.fromJson(c as Map<String, dynamic>));

    _flags = {for (final f in flagList) f.name: f};
    _configs = {for (final c in configList) c.key: c};

    if (!_updatesController.isClosed) {
      _updatesController.add(null);
    }
  }

  /// Returns true if [flagName] is currently ON for [userId].
  /// Returns [defaultValue] if the flag doesn't exist (e.g. not created yet).
  bool isEnabled(String flagName, {bool defaultValue = false}) {
    final flag = _flags[flagName];
    if (flag == null) return defaultValue;
    return flag.isEnabledFor(userId);
  }

  /// Returns the remote config value for [key], or [defaultValue] if the
  /// key doesn't exist. Works for both String and num (int/double) configs.
  T getConfig<T>(String key, T defaultValue) {
    final config = _configs[key];
    if (config == null) return defaultValue;

    final value = config.value;
    if (value is T) return value;
    if (defaultValue is double && value is num) return value.toDouble() as T;
    if (defaultValue is int && value is num) return value.toInt() as T;
    return defaultValue;
  }

  /// All known flags, keyed by name.
  Map<String, FeatureFlag> get flags => Map.unmodifiable(_flags);

  /// All known configs, keyed by key.
  Map<String, RemoteConfig> get configs => Map.unmodifiable(_configs);

  /// Closes the WebSocket connection. Call this in your widget's `dispose()`.
  void dispose() {
    _disposed = true;
    _channel?.sink.close();
    _updatesController.close();
  }
}
