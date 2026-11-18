"""初始化脚本必须只切换配置的数据库，不能误改 SQL 数据内容。"""
from scripts.init_db import SQL_FILES, split_statements, use_database_name


def test_init_targets_configured_database():
    commands = [
        use_database_name(statement, "jxrepair_isolated_test")
        for path in SQL_FILES
        for statement in split_statements(path.read_text(encoding="utf-8"))
    ]
    assert sum("USE `jxrepair_isolated_test`" in command for command in commands) == 2
    assert any("DROP DATABASE IF EXISTS `jxrepair_isolated_test`" in command for command in commands)
    assert any("CREATE DATABASE `jxrepair_isolated_test`" in command for command in commands)
    assert not any("USE cyf_jxrepair" in command for command in commands)


def test_database_identifier_quoted_without_changing_values():
    assert use_database_name("USE cyf_jxrepair", "name`with_tick") == "USE `name``with_tick`"
    statement = "INSERT INTO device (device_name) VALUES ('cyf_jxrepair');"
    assert use_database_name(statement, "other_db") == statement
