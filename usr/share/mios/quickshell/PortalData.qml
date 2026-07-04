// AI-hint: Native Quickshell client for the REAL MiOS Portal API (served by
// mios-agent-pipe at :8640 -- usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py).
// This is the first concrete step of the native-unification roadmap (design
// spec §"Native unification roadmap"): instead of embedding the Portal's
// HTML/iframe in a WebView, this talks to the SAME JSON endpoints
// (/login, /portal/stats, /portal/swarm) the web Portal already polls, and
// exposes the result as plain QML properties any panel (Sidebar.qml today;
// a future native Terminals/Services/Swarm view later) can bind to.
//
// Auth: portal.py gates /portal/* behind a signed session (design spec's
// native-unification addendum added Bearer-token support to
// _portal_authed()/portal_login_logic() alongside the existing browser
// cookie flow, specifically so a non-browser client doesn't need cookie-jar
// + redirect handling). Call login(password) once; the resulting token is
// held in memory only (never written to disk) and sent as
// 'Authorization: Bearer <token>' on every subsequent request. On a 401
// (session expired) `authed` flips back to false so the UI can re-prompt.
//
// AI-related: usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py,
// usr/share/mios/quickshell/Sidebar.qml, usr/share/mios/quickshell/Theme.qml
//
// Uses QML's built-in XMLHttpRequest (core Qt Quick JS environment, not a
// Quickshell-specific API) -- deliberately avoided relying on an unverified
// Quickshell HTTP helper here so this component's networking behavior is
// exactly what any Qt/QML app's XHR would do.

import QtQuick

QtObject {
    id: portal

    property string baseUrl: "http://127.0.0.1:8640"
    property string token: ""
    property bool authed: false
    property bool loading: false
    property string lastError: ""

    // Native mirrors of the web Portal's data -- shapes match portal.py's
    // portal_stats_logic / portal_swarm_logic JSON verbatim.
    property var stats: ({})
    property var swarmNodes: []

    property int refreshIntervalMs: 15000

    property Timer _poll: Timer {
        interval: portal.refreshIntervalMs
        running: portal.authed
        repeat: true
        onTriggered: portal.refresh()
    }

    function _request(method, path, body, onOk) {
        const xhr = new XMLHttpRequest()
        xhr.open(method, portal.baseUrl + path)
        if (body !== undefined) {
            xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded")
        }
        xhr.setRequestHeader("Accept", "application/json")
        if (portal.token.length > 0) {
            xhr.setRequestHeader("Authorization", "Bearer " + portal.token)
        }
        xhr.onreadystatechange = function () {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            portal.loading = false
            if (xhr.status === 401) {
                portal.authed = false
                portal.token = ""
                portal.lastError = "session expired -- call login() again"
                return
            }
            if (xhr.status < 200 || xhr.status >= 300) {
                portal.lastError = "HTTP " + xhr.status + " on " + path
                return
            }
            try {
                onOk(JSON.parse(xhr.responseText))
                portal.lastError = ""
            } catch (e) {
                portal.lastError = "bad JSON from " + path + ": " + e
            }
        }
        portal.loading = true
        xhr.send(body)
    }

    // Call with the operator's MiOS Portal password (same one Cockpit PAM
    // and the web Portal's /login page use -- mios.toml [identity]
    // .default_password / [portal].password). Never store the password
    // itself; only the resulting signed token is kept, in memory.
    function login(password) {
        _request("POST", "/login", "password=" + encodeURIComponent(password),
            function (json) {
                if (json.token) {
                    portal.token = json.token
                    portal.authed = true
                    portal.refresh()
                } else {
                    portal.lastError = json.error || "login failed"
                }
            })
    }

    function refresh() {
        if (!portal.authed) return
        _request("GET", "/portal/stats", undefined,
            function (json) { portal.stats = json })
        _request("GET", "/portal/swarm", undefined,
            function (json) { portal.swarmNodes = json.nodes || json.agents || json })
    }

    function logout() {
        token = ""
        authed = false
        stats = ({})
        swarmNodes = []
    }
}
