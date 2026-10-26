local sessions = {}

for _, key in ipairs(KEYS) do
    local value = redis.call("GET", key)

    if value then
        local user = cjson.decode(value)

        local row = "user_id=" .. tostring(user.user_id)
            .. " | username=" .. tostring(user.username or "(not stored)")
            .. " | ttl=" .. tostring(redis.call("TTL", key))

        table.insert(sessions, row)
    end
end

return sessions
