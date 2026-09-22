-- ---------------------------------------------------------------------------
-- Usuarios de demostración
--
-- GENERADO por model/tools/generar_semillas.py a partir de api/app/seed/.
-- No editar a mano: regenerar para mantener alineadas las tres capas.
-- ---------------------------------------------------------------------------

-- Contraseña de todas las cuentas de demostración: «demo».
-- Se almacena el hash Argon2id, nunca la contraseña.
INSERT INTO users (username, email, display_name, hashed_password, role_id) VALUES
    ('demo', 'demo@brainneuroscan.example', 'M. Rivera', '$argon2id$v=19$m=65536,t=3,p=4$ATd/pw7Kxgl2pNu+Mgka7Q$JLwdDmh5BE4GtjoUCJFXjOvOlv87Z6MIppZ0Q9UeDrw', (SELECT id FROM roles WHERE code = 'admin')),
    ('m.rivera', 'm.rivera@brainneuroscan.example', 'M. Rivera', '$argon2id$v=19$m=65536,t=3,p=4$lG87oqrr8GXdEcHLiStf9g$UzDdf+qqBs3fz1qIaVA/Tp7WrpKSOWIPiBpjb0NnXdc', (SELECT id FROM roles WHERE code = 'admin')),
    ('a.suarez', 'a.suarez@brainneuroscan.example', 'A. Suárez', '$argon2id$v=19$m=65536,t=3,p=4$VyemV7bbaP+dHoLqN4iDKQ$f3hSFyoDuyne/DBNgX2cqrp+MsvbRg9hEK8twXOh9H0', (SELECT id FROM roles WHERE code = 'researcher')),
    ('pipeline-ci', 'ci@brainneuroscan.example', 'Pipeline CI', '$argon2id$v=19$m=65536,t=3,p=4$nugkGFyqqlF32V8x2rZ6ZQ$Er5wtgiyyhwl2A+qaK+AQWgYxVJyvri2Xd7nNKz0jFA', (SELECT id FROM roles WHERE code = 'researcher'))
ON CONFLICT (username) DO NOTHING;
