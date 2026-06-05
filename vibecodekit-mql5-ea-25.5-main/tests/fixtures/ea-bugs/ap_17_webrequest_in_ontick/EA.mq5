//+--- ea-bugs fixture: AP-17 ---+
//| digits-tested: 5, 3 |
void OnTick() {
    char data[], result[];
    string hdr, resp_hdr;
    WebRequest("GET", "https://api.example.com", "", 5000,
               data, result, resp_hdr);   // BAD — blocks tick
}
