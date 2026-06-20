"""
수신부 JSON 프레이밍(_extract_json_objects) 오프라인 검증 테스트.

라즈베리파이 없이, 로그에서 관찰된 스트림 분할 패턴(len=4096 + len=252)을
재현해 파서가 올바르게 동작하는지 확인한다.

실행: python test_framing.py
"""
import json
import sys

# Windows cp949 콘솔에서 유니코드 출력 깨짐 방지
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from app.services.tcp_bridge import TCPBridgeService


def feed_stream(svc, chunks):
    """청크들을 순서대로 버퍼에 누적하며 _extract_json_objects를 반복 호출.
    실제 handle_receiver_connection 루프와 동일한 방식."""
    buffer = b""
    parsed = []
    for chunk in chunks:
        buffer += chunk
        objects, buffer = svc._extract_json_objects(buffer)
        parsed.extend(objects)
    return parsed, buffer


def make_big_sensor(order):
    """~4300바이트 SENSOR 패킷 생성 (유닛 32개 센서값 + ERROR 배열)."""
    values = []
    for tank in [601] + list(range(101, 132)):  # 32개 탱크
        for sid in range(1100, 1104):
            values.append({"TANK_ID": str(tank), "SENSOR_ID": str(sid), "VALUE": "0.00"})
    errors = [{"TANK_ID": str(t), "CODE": "0"} for t in [601] + list(range(101, 132))]
    return {"CMD": "SENSOR", "ORDER": str(order), "DATE": "2026-06-20",
            "TIME": "11:54:37", "VALUES": values, "ERROR": errors}


def make_ack(idx):
    return {"CMD": "ACK", "IDX": str(idx), "NOTE": "OK"}


def run():
    svc = TCPBridgeService()
    results = []

    def check(name, ok):
        results.append((name, ok))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    # 공통: 큰 SENSOR 1개 + 작은 ACK 2개 묶음
    big = json.dumps(make_big_sensor(162))
    ack1 = json.dumps(make_ack(328))
    ack2 = json.dumps(make_ack(329))
    assert len(big.encode()) > 4096, f"테스트 SENSOR가 4096B 이하임 ({len(big.encode())}B)"
    print(f"\n테스트 SENSOR 크기: {len(big.encode())} bytes")

    # ── 케이스 1: 구분자 없음(Pi 실제 동작) + 4096B 분할 ──────────────────────
    # big+ack1+ack2를 바이트로 이어붙인 뒤 4096씩 잘라 청크로 공급.
    print("\n[케이스 1] 구분자 없음 + 4096B 단위 분할 (Pi 실제 시나리오)")
    blob = (big + ack1 + ack2).encode()
    chunks = [blob[i:i + 4096] for i in range(0, len(blob), 4096)]
    parsed, remaining = feed_stream(svc, chunks)
    check("정확히 3개 객체 파싱", len(parsed) == 3)
    check("남은 버퍼 비어있음", remaining == b"")
    check("1번째는 SENSOR", json.loads(parsed[0])["CMD"] == "SENSOR" if parsed else False)
    check("ORDER 보존", json.loads(parsed[0])["ORDER"] == "162" if parsed else False)
    check("2,3번째는 ACK", len(parsed) == 3 and all(json.loads(p)["CMD"] == "ACK" for p in parsed[1:]))

    # ── 케이스 2: 개행 구분자 있음 (송신부 규약과 동일) ───────────────────────
    print("\n[케이스 2] 개행(\\n) 구분자 + 4096B 단위 분할")
    blob2 = (big + "\n" + ack1 + "\n" + ack2 + "\n").encode()
    chunks2 = [blob2[i:i + 4096] for i in range(0, len(blob2), 4096)]
    parsed2, remaining2 = feed_stream(svc, chunks2)
    check("정확히 3개 객체 파싱", len(parsed2) == 3)
    check("남은 버퍼 비어있음", remaining2 == b"")

    # ── 케이스 3: 로그 그대로 — 한 SENSOR가 4096 + 나머지로 쪼개짐 ────────────
    print("\n[케이스 3] SENSOR 1개가 4096B + 나머지로 분할 (로그 len=4096 + len=252)")
    sb = big.encode()
    parsed3, remaining3 = feed_stream(svc, [sb[:4096], sb[4096:]])
    check("최종 1개 객체 파싱", len(parsed3) == 1)
    check("남은 버퍼 비어있음", remaining3 == b"")

    # ── 케이스 4: 끝에 미완성 객체 — 보존되고 버려지지 않아야 함 ──────────────
    print("\n[케이스 4] 완전한 객체 2개 + 끝에 미완성 객체 (부분 수신 보존)")
    partial_blob = (ack1 + ack2 + big[:200]).encode()  # big의 앞 200B만 = 미완성
    parsed4, remaining4 = feed_stream(svc, [partial_blob])
    check("완전한 2개만 파싱", len(parsed4) == 2)
    check("미완성 객체는 버퍼에 보존(>0)", len(remaining4) > 0)
    # 이어서 나머지를 공급하면 3번째가 완성되어야 함
    parsed4b, remaining4b = feed_stream(svc, [remaining4 + big[200:].encode()])
    check("나머지 공급 후 3번째 SENSOR 완성", len(parsed4b) == 1 and json.loads(parsed4b[0])["CMD"] == "SENSOR")
    check("최종 버퍼 비어있음", remaining4b == b"")

    # ── 케이스 5: 바이트 단위(1B씩) 공급해도 동작 (극단적 분할) ───────────────
    print("\n[케이스 5] 1바이트씩 공급 (극단적 TCP 분할)")
    parsed5, remaining5 = feed_stream(svc, [bytes([b]) for b in ack1.encode()])
    check("1바이트씩 줘도 1개 완성", len(parsed5) == 1)
    check("최종 버퍼 비어있음", remaining5 == b"")

    # 결과 요약
    print("\n" + "=" * 50)
    failed = [n for n, ok in results if not ok]
    if failed:
        print(f"실패 {len(failed)}건: {failed}")
        return 1
    print(f"전체 {len(results)}건 통과 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(run())
