import json
import sqlite3
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
import deployment
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from deployment import patch_toml,patch_service,patch_basic_memory,Backup,restore

class Deployment(unittest.TestCase):
    def test_restore_recovers_original_budget_with_an_existing_wal_connection(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root=Path(temp);state=root/'state.sqlite'
            db=sqlite3.connect(state)
            try:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE settings(hourly_budget INTEGER)')
                db.execute('INSERT INTO settings VALUES(2)');db.commit()
                backup=Backup(root/'backup',[state]);backup.remember(state)
                db.execute('UPDATE settings SET hourly_budget=7');db.commit()
                restore(backup.folder)
                self.assertEqual(db.execute('SELECT hourly_budget FROM settings').fetchone()[0],2,
                    'Restoring the old budget must replace newer WAL changes consistently')
            finally:db.close()
    def test_claude_selects_shared_bridge_and_preserves_other_servers_and_login_settings(self):
        original={'mcpServers':{'basic-memory':{'type':'stdio','command':'basic-memory','args':['mcp'],
                'env':{'BASIC_MEMORY_CONFIG_DIR':'configured-vault'}},
                'other':{'type':'http','url':'https://example.invalid','headers':{'Authorization':'placeholder'}}},
                'oauthAccount':{'accountUuid':'fixture-account'},'projects':{'D:/a':{'trusted':True}}}
        transformed=deployment.patch_claude(original,'selected-python','shared-bridge.py')
        self.assertEqual(transformed['mcpServers']['basic-memory']['command'],'selected-python')
        self.assertEqual(transformed['mcpServers']['basic-memory']['args'],['shared-bridge.py'])
        self.assertEqual(transformed['mcpServers']['basic-memory']['env'],original['mcpServers']['basic-memory']['env'])
        self.assertEqual(transformed['mcpServers']['other'],original['mcpServers']['other'])
        self.assertEqual(transformed['oauthAccount'],original['oauthAccount'])
        self.assertEqual(transformed['projects'],original['projects'])
        self.assertEqual(original['mcpServers']['basic-memory']['command'],'basic-memory')
        self.assertEqual(deployment.patch_claude(transformed,'selected-python','shared-bridge.py'),transformed)
    def test_claude_remote_bank_is_not_replaced_by_a_local_memory_route(self):
        original={'mcpServers':{'basic-memory':{'type':'http','url':'https://example.invalid/mcp'}}}
        with self.assertRaises(ValueError):deployment.patch_claude(original,'python','bridge')
        self.assertEqual(original['mcpServers']['basic-memory']['url'],'https://example.invalid/mcp')
    def test_config_changes_preserve_other_servers_credentials_and_user_preferences(self):
        raw='model = "preferred-model"\n[mcp_servers.basic-memory]\ncommand = "old-python"\nargs = ["bridge.py"]\n[mcp_servers.other]\ncommand = "other-server"\n[features]\nhooks = false\nunrelated = true\n[model_providers.custom]\nbase_url = "https://example.invalid"\n'
        result=tomllib.loads(patch_toml(raw,'new-python'))
        self.assertEqual(result['mcp_servers']['basic-memory']['command'],'new-python')
        self.assertEqual(result['mcp_servers']['other']['command'],'other-server')
        self.assertEqual(result['model'],'preferred-model');self.assertTrue(result['features']['unrelated'])
        self.assertEqual(result['model_providers']['custom']['base_url'],'https://example.invalid')
        self.assertTrue(result['features']['hooks'])
    def test_config_alias_migrates_without_conflict_or_missing_table(self):
        raw='[mcp_servers.basic-memory]\ncommand="old"\n[features]\ncodex_hooks=false\nhooks=false\n'
        result=tomllib.loads(patch_toml(raw,'new'));self.assertEqual(result['features'],{'hooks':True})
        raw='[mcp_servers.basic-memory]\ncommand="old"\n'
        self.assertTrue(tomllib.loads(patch_toml(raw,'new'))['features']['hooks'])
    def test_budget_and_existing_projects_do_not_change_during_upgrade(self):
        config={'vault':'vault','max_calls_per_day':8,'reserve_tokens_per_call':12000,'sources':[{'kind':'claude','path':'history'}]}
        service=patch_service(config,'cache')
        for key in config:self.assertEqual(service[key],config[key])
        native={'projects':{'main':{'path':'vault'}},'cloud_api_key':'credential-placeholder','write_note_overwrite_default':False}
        result=patch_basic_memory(native,'cache')
        for key in native:self.assertEqual(result[key],native[key])
        self.assertEqual(result['semantic_embedding_dimensions'],384)
    def test_precise_backup_restore_recovers_previous_config_and_preserves_user_data(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root=Path(temp);target=root/'service';target.mkdir();config=target/'config.json';user=target/'user.md';new=target/'feature.py'
            config.write_text('{"budget":8}',encoding='utf-8');user.write_text('用户的原始笔记',encoding='utf-8')
            backup=Backup(root/'backup',[target]);backup.write(config,'{"budget":2}');backup.write(new,'new feature')
            with self.assertRaises(ValueError):backup.write(root/'outside','other data')
            restore(backup.folder)
            self.assertEqual(json.loads(config.read_text()),{'budget':8})
            self.assertEqual(user.read_text(encoding='utf-8'),'用户的原始笔记')
