import importlib.metadata

from dataclasses import dataclass
from typing import Any, Optional

from textual.widget import Widget
from textual.screen import Screen

from termdash.api import TermDashPlugin


@dataclass
class PluginError:
    """Represents an error that occurred during discovery or loading."""
    plugin_id: str
    stage: str  # "discover" | "load"
    error: Exception
    message: str


class PluginManager:
    """
    Discovers and loads TermDash plugins.

    Plugins are discovered using Python entrypoints under ENTRYPOINT_GROUP.
    Plugins are enabled/disabled using the TermDash config.toml under [modules.*].
    """

    ENTRYPOINT_GROUP = "termdash.plugins"

    def __init__(self) -> None:
        self.plugins: dict[str, TermDashPlugin] = {}
        self.errors: list[PluginError] = []

    # -------------------------
    # Discovery / Query Methods
    # -------------------------

    def discover(self) -> dict[str, TermDashPlugin]:
        """
        Discover installed TermDash plugins via entrypoints.

        Returns:
            dict[str, TermDashPlugin]: plugin_id -> plugin object
        """
        self.plugins.clear()

        try:
            eps = importlib.metadata.entry_points(group=self.ENTRYPOINT_GROUP)
        except Exception as e:
            self.errors.append(
                PluginError(
                    plugin_id="*",
                    stage="discover",
                    error=e,
                    message=f"Failed to read entry points group '{self.ENTRYPOINT_GROUP}'"
                )
            )
            return self.plugins

        for ep in eps:
            try:
                plugin_obj = ep.load()
            except Exception as e:
                self.errors.append(
                    PluginError(
                        plugin_id=ep.name,
                        stage="discover",
                        error=e,
                        message=f"Failed to import plugin entrypoint '{ep.name}'"
                    )
                )
                continue

            # Validate the plugin type
            if not isinstance(plugin_obj, TermDashPlugin):
                self.errors.append(
                    PluginError(
                        plugin_id=getattr(plugin_obj, "id", ep.name),
                        stage="discover",
                        error=TypeError("Invalid plugin type"),
                        message=f"Entrypoint '{ep.name}' did not return a TermDashPlugin object"
                    )
                )
                continue

            # Ensure plugin.id is unique
            if plugin_obj.id in self.plugins:
                self.errors.append(
                    PluginError(
                        plugin_id=plugin_obj.id,
                        stage="discover",
                        error=ValueError("Duplicate plugin id"),
                        message=f"Duplicate plugin id '{plugin_obj.id}' found. Skipping."
                    )
                )
                continue

            self.plugins[plugin_obj.id] = plugin_obj

        return self.plugins

    def list_plugins(self) -> list[TermDashPlugin]:
        """Return all discovered plugins."""
        return list(self.plugins.values())

    def get_plugin(self, plugin_id: str) -> Optional[TermDashPlugin]:
        """Return a plugin if installed, else None."""
        return self.plugins.get(plugin_id)

    def is_installed(self, plugin_id: str) -> bool:
        """Return True if a plugin is installed/discovered."""
        return plugin_id in self.plugins

    # -------------------------
    # Config Parsing Helpers
    # -------------------------

    def get_configured_plugins(self, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Reads the [modules] section of the config and returns a flattened mapping.

        Example TOML:
            [modules.core.weather]
            enabled = true

        Parsed dict:
            {"modules": {"core": {"weather": {"enabled": True}}}}

        Returned mapping:
            {"core.weather": {"enabled": True}}
        """
        modules = config.get("modules")

        if not isinstance(modules, dict):
            return {}

        flat: dict[str, dict[str, Any]] = {}

        def walk(prefix: str, node: dict[str, Any]) -> None:
            for key, value in node.items():
                if not isinstance(key, str):
                    continue

                if isinstance(value, dict):
                    plugin_id = f"{prefix}.{key}" if prefix else key

                    # If this dict looks like a plugin config table, store it.
                    if "enabled" in value:
                        flat[plugin_id] = value
                    else:
                        # Otherwise treat it as a namespace and recurse.
                        walk(plugin_id, value)

        walk("", modules)
        return flat

    def get_enabled_plugin_ids(self, config: dict[str, Any]) -> list[str]:
        """
        Returns a list of enabled plugin IDs from config.

        Rules:
        - enabled defaults to False if missing
        - enabled must be a bool, otherwise treated as invalid
        """
        configured = self.get_configured_plugins(config)
        enabled_plugins: list[str] = []

        for plugin_id, plugin_cfg in configured.items():
            enabled = plugin_cfg.get("enabled", False)

            if enabled is True:
                enabled_plugins.append(plugin_id)

            elif enabled is not False:
                self.errors.append(
                    PluginError(
                        plugin_id=plugin_id,
                        stage="load",
                        error=TypeError("enabled must be bool"),
                        message=f"Invalid config: plugin '{plugin_id}' has non-boolean 'enabled' value: {enabled!r}"
                    )
                )

        return enabled_plugins

    def is_enabled(self, plugin_id: str, config: dict[str, Any]) -> bool:
        """
        Returns True if plugin is enabled in config.

        Rules:
        - Missing plugin config => False
        - enabled defaults to False if missing
        - enabled must be a bool, otherwise False
        """
        configured = self.get_configured_plugins(config)
        plugin_cfg = configured.get(plugin_id)

        if not isinstance(plugin_cfg, dict):
            return False

        enabled = plugin_cfg.get("enabled", False)

        if not isinstance(enabled, bool):
            self.errors.append(
                PluginError(
                    plugin_id=plugin_id,
                    stage="load",
                    error=TypeError("enabled must be bool"),
                    message=f"Invalid config: plugin '{plugin_id}' has non-boolean 'enabled' value: {enabled!r}"
                )
            )
            return False

        return enabled

    # -------------------------
    # Loading Methods
    # -------------------------

    def load_plugin(
        self,
        plugin_id: str,
        app: Any,
        config: dict[str, Any],
    ) -> Widget | Screen | None:
        """
        Loads a plugin by ID regardless of enabled/disabled state.
        Enabled/disabled logic should be handled by load_enabled().

        Returns:
            Widget | Screen if successful, else None
        """
        plugin = self.get_plugin(plugin_id)

        if plugin is None:
            self.errors.append(
                PluginError(
                    plugin_id=plugin_id,
                    stage="load",
                    error=KeyError("Plugin not installed"),
                    message=f"Plugin '{plugin_id}' is not installed or not discoverable."
                )
            )
            return None

        configured = self.get_configured_plugins(config)
        plugin_cfg = configured.get(plugin_id, {})

        if not isinstance(plugin_cfg, dict):
            plugin_cfg = {}

        # Create plugin instance
        try:
            instance = plugin.factory(app, plugin_cfg)
        except Exception as e:
            self.errors.append(
                PluginError(
                    plugin_id=plugin_id,
                    stage="load",
                    error=e,
                    message=f"Plugin '{plugin_id}' factory raised an exception."
                )
            )
            return None

        # Validate instance type matches plugin_type
        if plugin.plugin_type == "widget":
            if not isinstance(instance, Widget):
                self.errors.append(
                    PluginError(
                        plugin_id=plugin_id,
                        stage="load",
                        error=TypeError("Invalid plugin return type"),
                        message=f"Plugin '{plugin_id}' is type 'widget' but factory returned {type(instance).__name__}"
                    )
                )
                return None

        elif plugin.plugin_type == "page":
            if not isinstance(instance, Screen):
                self.errors.append(
                    PluginError(
                        plugin_id=plugin_id,
                        stage="load",
                        error=TypeError("Invalid plugin return type"),
                        message=f"Plugin '{plugin_id}' is type 'page' but factory returned {type(instance).__name__}"
                    )
                )
                return None

        else:
            self.errors.append(
                PluginError(
                    plugin_id=plugin_id,
                    stage="load",
                    error=ValueError("Unknown plugin type"),
                    message=f"Plugin '{plugin_id}' has unknown plugin_type: {plugin.plugin_type}"
                )
            )
            return None

        return instance

    def load_enabled(
        self,
        app: Any,
        config: dict[str, Any],
    ) -> list[Widget | Screen]:
        """
        Loads all plugins enabled in config.

        Returns:
            list of successfully loaded plugin instances
        """
        loaded: list[Widget | Screen] = []

        enabled_ids = sorted(self.get_enabled_plugin_ids(config))

        for plugin_id in enabled_ids:
            if not self.is_installed(plugin_id):
                self.errors.append(
                    PluginError(
                        plugin_id=plugin_id,
                        stage="load",
                        error=KeyError("Plugin enabled but not installed"),
                        message=f"Plugin '{plugin_id}' is enabled in config but not installed."
                    )
                )
                continue

            instance = self.load_plugin(plugin_id, app, config)

            if instance is not None:
                loaded.append(instance)

        return loaded

    # -------------------------
    # Error Handling / Reporting
    # -------------------------

    def get_errors(self) -> list[PluginError]:
        """Returns all errors collected so far."""
        return self.errors

    def clear_errors(self) -> None:
        """Clears the internal error list."""
        self.errors.clear()
