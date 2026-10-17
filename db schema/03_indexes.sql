-- SafeSite Vision - Performance Indexes for MySQL 8.0
-- Host: localhost:3306 | User: root

USE safesitevision;

-- Helper procedure to safely add index if it doesn't already exist
DROP PROCEDURE IF EXISTS AddIndexIfNotExists;
DELIMITER $$
CREATE PROCEDURE AddIndexIfNotExists(
    IN tableName VARCHAR(64),
    IN indexName VARCHAR(64),
    IN indexColumns VARCHAR(255)
)
BEGIN
    DECLARE idxCount INT;
    SELECT COUNT(*) INTO idxCount
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = tableName
      AND index_name = indexName;
      
    IF idxCount = 0 THEN
        SET @sql = CONCAT('CREATE INDEX ', indexName, ' ON ', tableName, ' (', indexColumns, ')');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- Indexes for violation_events
CALL AddIndexIfNotExists('violation_events', 'ix_events_time', 'occurred_at DESC');
CALL AddIndexIfNotExists('violation_events', 'ix_events_zone_rule', 'zone_id, rule, occurred_at DESC');
CALL AddIndexIfNotExists('violation_events', 'ix_events_camera', 'camera_id, occurred_at DESC');
CALL AddIndexIfNotExists('violation_events', 'ix_events_status', 'status');
CALL AddIndexIfNotExists('violation_events', 'ix_events_track', 'track_id');

-- Indexes for episodes
CALL AddIndexIfNotExists('episodes', 'ix_episodes_camera_state', 'camera_id, state');
CALL AddIndexIfNotExists('episodes', 'ix_episodes_track', 'camera_id, track_id');
CALL AddIndexIfNotExists('episodes', 'ix_episodes_time', 'last_seen_at DESC');

-- Indexes for cameras and zones
CALL AddIndexIfNotExists('cameras', 'ix_cameras_status', 'status, is_enabled');
CALL AddIndexIfNotExists('zones', 'ix_zones_camera', 'camera_id, priority');

-- Indexes for reviews and feedback
CALL AddIndexIfNotExists('reviews', 'ix_reviews_event', 'event_id');
CALL AddIndexIfNotExists('feedback_samples', 'ix_feedback_exported', 'exported, kind');
CALL AddIndexIfNotExists('audit_log', 'ix_audit_user_time', 'user_id, created_at DESC');

DROP PROCEDURE IF EXISTS AddIndexIfNotExists;
