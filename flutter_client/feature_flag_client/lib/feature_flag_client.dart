/// Real-time client for the self-hosted Feature Flag & Remote Config Engine.
///
/// ```dart
/// import 'package:feature_flag_client/feature_flag_client.dart';
///
/// final client = FeatureFlagClient(
///   baseUrl: 'http://192.168.1.50:8000',
///   userId: 'user_42',
/// );
/// await client.connect();
///
/// if (client.isEnabled('dark_mode_beta')) {
///   // show the dark theme
/// }
///
/// final welcome = client.getConfig<String>('welcome_message', 'Hello!');
///
/// // Rebuild your UI whenever the server pushes a change:
/// client.updates.listen((_) => setState(() {}));
/// ```
library feature_flag_client;

export 'src/client.dart';
export 'src/models.dart';
