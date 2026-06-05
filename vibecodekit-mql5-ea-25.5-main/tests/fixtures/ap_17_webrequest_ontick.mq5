//+------------------------------------------------------------------+
//| Fixture: AP-17 WebRequest-in-OnTick                                |
//| /mql5-lint MUST detect this as ERROR.                             |
//+------------------------------------------------------------------+
void OnTick() {
    char data[], result[];
    string headers, response_headers;
    // BAD — WebRequest blocks OnTick; AP-17 violation
    int code = WebRequest("GET", "https://api.example.com/signal", "", 5000,
                          data, result, response_headers);
}
