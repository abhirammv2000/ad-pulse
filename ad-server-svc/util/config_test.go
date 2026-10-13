package util

import "testing"

// viper's AutomaticEnv only resolves keys it already knows about, so a field that is added to Config but not to
// defaults silently never reads its environment variable. These tests catch that for the manager key.

func TestLoadConfig_ReadsTheManagerAPIKeyFromTheEnvironment(t *testing.T) {
	t.Setenv("AD_MANAGER_API_KEY", "a-key-from-the-environment")

	config, err := LoadConfig(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	if config.AdManagerAPIKey != "a-key-from-the-environment" {
		t.Errorf("AdManagerAPIKey = %q, want the value of AD_MANAGER_API_KEY", config.AdManagerAPIKey)
	}
}

func TestLoadConfig_TheManagerAPIKeyDefaultsToEmpty(t *testing.T) {
	t.Setenv("AD_MANAGER_API_KEY", "")

	config, err := LoadConfig(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	if config.AdManagerAPIKey != "" {
		t.Errorf("AdManagerAPIKey = %q, want empty", config.AdManagerAPIKey)
	}
}
