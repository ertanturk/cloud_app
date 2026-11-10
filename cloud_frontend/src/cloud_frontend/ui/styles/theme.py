APP_CSS = """
Screen {
    background: #292522;
    color: #ECE1D7;
}

LoginScreen {
    align: center middle;
}

Header, Footer {
    background: #34302C;
    color: #ECE1D7;
}

Footer {
    dock: bottom;
    height: 2;
    border-top: solid #867462;
}

.surface {
    background: #34302C;
    border: round #867462;
    margin: 1;
    padding: 1;
}

.screen-title {
    color: #F2C14E;
    text-style: bold;
    text-align: center;
    width: 100%;
}

.screen-subtitle {
    color: #C1A78E;
    text-align: center;
    width: 100%;
}

.section-title {
    color: #F2C14E;
    text-style: bold;
    margin: 1 0 0 1;
}

.help-text {
    color: #C1A78E;
    margin: 0 1;
}

.instructions {
    background: #403A36;
    border: round #6B5B4D;
    margin: 1;
    padding: 1;
}

.primary {
    background: #F2C14E;
    color: #292522;
    text-style: bold;
}

.raised {
    background: #403A36;
    border: round #C1A78E;
    margin: 1;
    padding: 1;
}

Input, Select {
    margin: 1;
}

Button {
    margin: 1;
    background: #403A36;
    color: #ECE1D7;
}

.upload {
    background: #A3A9CE;
    color: #292522;
}

.download {
    background: #85B695;
    color: #292522;
}

.remove {
    background: #D47766;
    color: #292522;
}

.error {
    color: #D47766;
    text-style: bold;
}

.success {
    color: #85B695;
}

.info {
    color: #A3A9CE;
}

#login-message, #message, #admin-message {
    min-height: 2;
    margin: 1;
}

.metric {
    width: 1fr;
    min-height: 10;
    height: 1fr;
    margin: 1;
    padding: 1;
    background: #403A36;
    border: round #867462;
    overflow-y: auto;
}

.admin-menu {
    width: 100%;
}

.admin-menu Button {
    width: 1fr;
    height: 3;
    min-height: 3;
    content-align: center middle;
}

.qr {
    color: #FFFFFF;
    width: auto;
    height: auto;
    min-height: 1;
    margin: 1;
}

#telemetry-content {
    height: 1fr;
}

#telemetry-content Horizontal {
    height: auto;
}

#user-actions {
    height: auto;
    min-height: 8;
    margin: 0 1;
}

#user-actions Horizontal {
    height: auto;
}

#user-id, #quota {
    width: 1fr;
}

DataTable {
    height: 1fr;
    margin: 1;
    background: #34302C;
    border: round #867462;
    color: #ECE1D7;
}

DataTable > .datatable--header {
    background: #6B5B4D;
    color: #FFF8EE;
    text-style: bold;
}

Input:focus {
    border: tall #F2C14E;
}
"""
