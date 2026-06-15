// Example app for the feature_flag_client package.
//
// HOW TO USE THIS FILE:
//   1. Create a normal Flutter app:  flutter create feature_flag_example
//   2. Add a path dependency on this package in its pubspec.yaml (see
//      flutter_client/example_app/pubspec_snippet.yaml for the exact lines).
//   3. Replace the generated lib/main.dart with this file.
//   4. Run it:  flutter run
//
// While it's running, open the terminal dashboard (tui/app.py), toggle a
// flag or edit "welcome_message", and watch this screen update instantly —
// no refresh, no restart.

import 'package:flutter/material.dart';
import 'package:feature_flag_client/feature_flag_client.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Feature Flag Demo',
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  // Point this at the machine running the Python backend:
  //  - Android emulator  -> http://10.0.2.2:8000
  //  - iOS simulator     -> http://localhost:8000
  //  - Physical device   -> http://<your-computer-LAN-IP>:8000
  //  - Web / desktop     -> http://localhost:8000
  late final FeatureFlagClient _client = FeatureFlagClient(
    baseUrl: 'http://localhost:8000',
    userId: 'beta_user_1',
  );

  late final TextEditingController _userIdController;
  bool _connected = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _userIdController = TextEditingController(text: _client.userId ?? '');
    _client
        .connect()
        .then((_) => setState(() => _connected = true))
        .catchError((e) => setState(() => _error = e.toString()));

    _client.updates.listen((_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _userIdController.dispose();
    _client.dispose();
    super.dispose();
  }

  void _updateUser(String? userId) {
    setState(() {
      _client.userId = userId;
      _userIdController.text = userId ?? '';
    });
  }

  Widget _buildUserBadge(String? userId) {
    if (userId == null || userId.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          border: Border.all(color: Colors.grey.shade400),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.person_outline, size: 14, color: Colors.grey.shade600),
            const SizedBox(width: 4),
            Text(
              'Guest',
              style: TextStyle(
                color: Colors.grey.shade700,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      );
    }

    final isBetaUser = _client.flags.values.any((f) => f.rollout.betaUserIds.contains(userId));

    if (isBetaUser) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [Colors.purple.shade700, Colors.deepPurple.shade900],
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.purple.withOpacity(0.3),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.star, size: 14, color: Colors.amber),
            SizedBox(width: 4),
            Text(
              'Beta Tier',
              style: TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        border: Border.all(color: Colors.blue.shade300),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.verified_user_outlined, size: 14, color: Colors.blue.shade700),
          const SizedBox(width: 4),
          Text(
            'Standard Tier',
            style: TextStyle(
              color: Colors.blue.shade800,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickUserButton(String? targetUserId, String label, {bool isDestructive = false}) {
    final isSelected = _client.userId == targetUserId;
    return OutlinedButton(
      onPressed: () => _updateUser(targetUserId),
      style: OutlinedButton.styleFrom(
        backgroundColor: isSelected
            ? (isDestructive ? Colors.red.shade50 : Colors.indigo.shade50)
            : null,
        side: BorderSide(
          color: isSelected
              ? (isDestructive ? Colors.red.shade400 : Colors.indigo.shade400)
              : Colors.grey.shade300,
          width: isSelected ? 1.5 : 1,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isSelected
              ? (isDestructive ? Colors.red.shade800 : Colors.indigo.shade800)
              : Colors.black87,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          fontSize: 12,
        ),
      ),
    );
  }

  Widget _buildIdentityCard() {
    return Card(
      elevation: 4,
      shadowColor: Colors.indigo.withOpacity(0.2),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.indigo.withOpacity(0.2), width: 1.5),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                Colors.indigo.withOpacity(0.05),
                Colors.purple.withOpacity(0.05),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'User Identity',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Colors.indigo.shade800,
                        ),
                  ),
                  _buildUserBadge(_client.userId),
                ],
              ),
              const SizedBox(height: 12),
              RichText(
                text: TextSpan(
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.black87),
                  children: [
                    const TextSpan(text: 'Current User ID: '),
                    TextSpan(
                      text: _client.userId ?? 'None (Anonymous Guest)',
                      style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.indigo),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Quick Switch User:',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey.shade600,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildQuickUserButton('beta_user_1', 'Beta User 1'),
                  _buildQuickUserButton('beta_user_2', 'Beta User 2'),
                  _buildQuickUserButton('standard_user', 'Standard User'),
                  _buildQuickUserButton(null, 'Clear/Guest', isDestructive: true),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 12),
              Text(
                'Custom Login / Session:',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey.shade600,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _userIdController,
                      decoration: InputDecoration(
                        isDense: true,
                        hintText: 'Enter custom User ID',
                        prefixIcon: const Icon(Icons.person_outline),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 12,
                        ),
                      ),
                      onSubmitted: (value) {
                        _updateUser(value.trim().isEmpty ? null : value.trim());
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: () {
                      final text = _userIdController.text.trim();
                      _updateUser(text.isEmpty ? null : text);
                    },
                    icon: const Icon(Icons.login),
                    label: const Text('Apply'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.indigo,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Feature Flag Demo')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Could not connect to the backend:\n$_error\n\n'
              'Make sure the server is running and baseUrl is correct.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    if (!_connected) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final welcomeMessage = _client.getConfig<String>('welcome_message', 'Hello!');
    final maxLoginAttempts = _client.getConfig<int>('max_login_attempts', 3);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Feature Flag Demo'),
        centerTitle: true,
        backgroundColor: Colors.indigo.shade50,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildIdentityCard(),
          const SizedBox(height: 24),
          Text(
            'Remote Configs',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Card(
            elevation: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    welcomeMessage,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Colors.indigo.shade900,
                        ),
                  ),
                  const SizedBox(height: 12),
                  const Divider(),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Max Login Attempts:',
                        style: TextStyle(fontWeight: FontWeight.w500, color: Colors.black54),
                      ),
                      Chip(
                        label: Text('$maxLoginAttempts'),
                        backgroundColor: Colors.indigo.shade50,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Live Feature Flags',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          _FlagTile(
            client: _client,
            flagName: 'new_checkout_flow',
            label: 'New checkout flow',
            icon: Icons.shopping_cart_checkout,
            color: Colors.green,
          ),
          _FlagTile(
            client: _client,
            flagName: 'dark_mode_beta',
            label: 'Dark mode (beta)',
            icon: Icons.dark_mode,
            color: Colors.deepPurple,
          ),
          _FlagTile(
            client: _client,
            flagName: 'ai_recommendations',
            label: 'AI recommendations',
            icon: Icons.auto_awesome,
            color: Colors.orange,
          ),
        ],
      ),
    );
  }
}

/// A row that shows whether a feature flag is ON or OFF for this user,
/// right now, in real time.
class _FlagTile extends StatelessWidget {
  final FeatureFlagClient client;
  final String flagName;
  final String label;
  final IconData icon;
  final Color color;

  const _FlagTile({
    required this.client,
    required this.flagName,
    required this.label,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final isOn = client.isEnabled(flagName);

    return Card(
      color: isOn ? color.withOpacity(0.15) : null,
      child: ListTile(
        leading: Icon(icon, color: isOn ? color : Colors.grey),
        title: Text(label),
        subtitle: Text(flagName),
        trailing: Chip(
          label: Text(isOn ? 'ON' : 'OFF'),
          backgroundColor: isOn ? color : Colors.grey.shade300,
          labelStyle: TextStyle(color: isOn ? Colors.white : Colors.black54),
        ),
      ),
    );
  }
}
