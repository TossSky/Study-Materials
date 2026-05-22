#!/bin/bash
# Прогон функциональных тестов всех 5 программ против эталонных Ruby-эмуляторов.
# Запуск в WSL. Требует ruby в PATH.
# Использование: bash run_all_tests.sh

set -e
cd "$(dirname "$0")"

STUBS=../stubs
PASS=0
FAIL=0
FAIL_NAMES=()

# -----------------------------------------------------------------------------
# Утилиты
# -----------------------------------------------------------------------------
log() { echo "[$(date +%T)] $*"; }

run_test() {
    local name="$1"
    log "=== $name ==="
    rm -f msg.txt got.txt srv_emul.log cli_emul.log
}

assert_msgs() {
    local name="$1"; local expected="$2"
    local got_lines
    got_lines=$(wc -l < msg.txt 2>/dev/null || echo 0)
    if [ "$got_lines" -eq "$expected" ]; then
        PASS=$((PASS + 1))
        log "  PASS: $name ($got_lines msgs)"
    else
        FAIL=$((FAIL + 1))
        FAIL_NAMES+=("$name (expected $expected, got $got_lines)")
        log "  FAIL: $name (expected $expected, got $got_lines)"
    fi
}

wait_port() {
    for _ in $(seq 1 20); do
        ss -ltnu 2>/dev/null | grep -q ":$1 " && return 0
        sleep 0.1
    done
    return 1
}

PORT_TCP=19000
PORT_UDP=19010

# -----------------------------------------------------------------------------
# TCP CLIENT: tcpclient (Linux) → tcpserveremul.rb (Linux)
# -----------------------------------------------------------------------------

# T1: 4 валидных + 1 пустая + stop
run_test "T1 tcpclient: 4 msgs + stop"
cat > t1.txt <<'EOF'
+70001234567 +79991234567 12:44:51 hello world
+71112223344 +75556667788 23:59:59 boundary time

+70000000000 +79999999999 00:00:00 zero time
+70001234567 +79991234567 13:41:59 stop
EOF
ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_TCP
./tcpclient 127.0.0.1:$PORT_TCP t1.txt > cli_emul.log 2>&1
wait $SRV_PID 2>/dev/null || true
assert_msgs "T1" 4

# T2: пустой файл
PORT_TCP=$((PORT_TCP + 1))
run_test "T2 tcpclient: empty file"
: > t2.txt
ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_TCP
./tcpclient 127.0.0.1:$PORT_TCP t2.txt > cli_emul.log 2>&1
sleep 0.3
kill $SRV_PID 2>/dev/null || true
wait $SRV_PID 2>/dev/null || true
assert_msgs "T2" 0

# T3: только пустые строки
PORT_TCP=$((PORT_TCP + 1))
run_test "T3 tcpclient: only empty lines"
printf '\n\n\n' > t3.txt
ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_TCP
./tcpclient 127.0.0.1:$PORT_TCP t3.txt > cli_emul.log 2>&1
sleep 0.3
kill $SRV_PID 2>/dev/null || true
wait $SRV_PID 2>/dev/null || true
assert_msgs "T3" 0

# T4: длинное сообщение
PORT_TCP=$((PORT_TCP + 1))
run_test "T4 tcpclient: long message"
LONG=$(python3 -c "print('a' * 1500)")
{ echo "+70001234567 +79991234567 12:00:00 $LONG"
  echo "+70001234567 +79991234567 13:00:00 stop"; } > t4.txt
ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_TCP
./tcpclient 127.0.0.1:$PORT_TCP t4.txt > cli_emul.log 2>&1
wait $SRV_PID 2>/dev/null || true
assert_msgs "T4" 2

# T5: сервер запускается с задержкой (проверка ретраев connect)
PORT_TCP=$((PORT_TCP + 1))
run_test "T5 tcpclient: retry connect"
cat > t5.txt <<'EOF'
+70001234567 +79991234567 13:41:59 stop
EOF
( sleep 0.5 && ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 ) &
SRV_PID=$!
./tcpclient 127.0.0.1:$PORT_TCP t5.txt > cli_emul.log 2>&1
wait $SRV_PID 2>/dev/null || true
assert_msgs "T5" 1

# T6: 3 параллельных клиента
PORT_TCP=$((PORT_TCP + 1))
run_test "T6 tcpclient: 3 parallel clients"
for n in 1 2 3; do
    cat > "t6_c${n}.txt" <<EOF
+7000000000${n} +7999999999${n} 10:0${n}:00 client${n} msg a
+7000000000${n} +7999999999${n} 10:0${n}:01 client${n} msg b
EOF
done
echo "+70001234567 +79991234567 13:41:59 stop" > t6_stop.txt
ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_TCP
./tcpclient 127.0.0.1:$PORT_TCP t6_c1.txt > t6_c1.log 2>&1 &
./tcpclient 127.0.0.1:$PORT_TCP t6_c2.txt > t6_c2.log 2>&1 &
./tcpclient 127.0.0.1:$PORT_TCP t6_c3.txt > t6_c3.log 2>&1 &
wait
./tcpclient 127.0.0.1:$PORT_TCP t6_stop.txt > t6_stop.log 2>&1
wait $SRV_PID 2>/dev/null || true
assert_msgs "T6" 7

# -----------------------------------------------------------------------------
# TCP CLIENT2 (доп. задание): tcpclient2 (Linux) → tcpserveremul.rb
# -----------------------------------------------------------------------------

# T7: get при наполненном msg.txt
PORT_TCP=$((PORT_TCP + 1))
run_test "T7 tcpclient2: get with data"
# наполним msg.txt предыдущим раундом
cat > t7_put.txt <<'EOF'
+70001234567 +79991234567 12:44:51 first stored
+70001234567 +79991234567 12:44:52 second stored
+70001234567 +79991234567 13:41:59 stop
EOF
ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_TCP
./tcpclient 127.0.0.1:$PORT_TCP t7_put.txt > /dev/null 2>&1
wait $SRV_PID 2>/dev/null || true
# теперь get
PORT_TCP=$((PORT_TCP + 1))
ruby $STUBS/tcpserveremul.rb $PORT_TCP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_TCP
./tcpclient2 127.0.0.1:$PORT_TCP get got.txt > cli_emul.log 2>&1
sleep 0.3
kill $SRV_PID 2>/dev/null || true
wait $SRV_PID 2>/dev/null || true
got_lines=$(wc -l < got.txt 2>/dev/null || echo 0)
if [ "$got_lines" -eq 3 ]; then
    PASS=$((PASS + 1)); log "  PASS: T7 (got 3 stored msgs)"
else
    FAIL=$((FAIL + 1)); FAIL_NAMES+=("T7 (got $got_lines, expected 3)"); log "  FAIL: T7"
fi

# -----------------------------------------------------------------------------
# UDP SERVER: udpserver (Linux) ← udpclientemul.rb (Linux)
# -----------------------------------------------------------------------------

# T8: 5 сообщений, один порт
PORT_UDP=$((PORT_UDP + 1))
run_test "T8 udpserver: 5 msgs, 1 port"
cat > t8.txt <<'EOF'
+70001234567 +79991234567 12:00:01 m1
+70001234567 +79991234567 12:00:02 m2
+70001234567 +79991234567 12:00:03 m3
+70001234567 +79991234567 12:00:04 m4
+70001234567 +79991234567 13:41:59 stop
EOF
./udpserver $PORT_UDP $PORT_UDP > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_UDP
ruby $STUBS/udpclientemul.rb 127.0.0.1:$PORT_UDP t8.txt > cli_emul.log 2>&1
wait $SRV_PID 2>/dev/null || true
assert_msgs "T8" 5

# T9: диапазон портов, клиенты на разные
PORT_UDP=$((PORT_UDP + 1))
PORT_UDP_END=$((PORT_UDP + 2))
run_test "T9 udpserver: port range"
cat > t9_a.txt <<EOF
+70001234567 +79991234567 12:00:01 from port A
EOF
cat > t9_b.txt <<EOF
+70001234567 +79991234567 12:00:02 from port B
EOF
echo "+70001234567 +79991234567 13:41:59 stop" > t9_stop.txt
./udpserver $PORT_UDP $PORT_UDP_END > srv_emul.log 2>&1 &
SRV_PID=$!
wait_port $PORT_UDP
ruby $STUBS/udpclientemul.rb 127.0.0.1:$PORT_UDP     t9_a.txt > t9_a.log 2>&1
ruby $STUBS/udpclientemul.rb 127.0.0.1:$((PORT_UDP+1)) t9_b.txt > t9_b.log 2>&1
ruby $STUBS/udpclientemul.rb 127.0.0.1:$PORT_UDP     t9_stop.txt > /dev/null 2>&1
wait $SRV_PID 2>/dev/null || true
assert_msgs "T9" 3

# -----------------------------------------------------------------------------
# Итог
# -----------------------------------------------------------------------------
log "================================================================="
log "TOTAL: PASS=$PASS  FAIL=$FAIL"
if [ "${#FAIL_NAMES[@]}" -gt 0 ]; then
    log "Failed tests:"
    for f in "${FAIL_NAMES[@]}"; do log "  - $f"; done
fi
[ "$FAIL" -eq 0 ]
