/*
Table that stores a list of valid plugins that can be installed by tdpm.
*/
CREATE TABLE IF NOT EXISTS plugins (
       id INTEGER PRIMARY KEY,	-- Internal ID in the DB

       pluginID TEXT NOT NULL,	-- The id of the plugin i.e. "com.user.plugin-name"
       name TEXT NOT NULL,	-- The name of the plugin. i.e. "plugin-name"
       author TEXT NOT NULL,	-- The author of the plugin.
       source TEXT NOT NULL,	-- Where to install the plugin from. i.e. "https://github.com/JMinyard1335/TermDash_Core.Time"
       
       addedOn TEXT NOT NULL,	-- date the plugin was added to the plugin list
       updatedOn TEXT NOT NULL, -- The last time the plugin was updated.
);
