import time
import traceback
import database
import oci_genai
from typing import Optional, Dict

def _update_system_health(service_name: str, status: str, latency_ms: Optional[int], error_msg: Optional[str]) -> None:
    """
    Updates one row in SYSTEM_HEALTH for the given service.
    """
    conn = None
    cursor = None
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE SYSTEM_HEALTH
            SET STATUS = :status,
                LAST_CHECKED = SYSTIMESTAMP,
                LATENCY_MS = :latency_ms,
                ERROR_MSG = :error_msg
            WHERE SERVICE_NAME = :service_name
            """,
            {
                "status": status,
                "latency_ms": latency_ms,
                "error_msg": error_msg,
                "service_name": service_name,
            },
        )

        conn.commit()

    except Exception as e:
        print(f"[SYSTEM_HEALTH UPDATE ERROR] {service_name}: {e}")
        print(traceback.format_exc())

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def perform_health_checks() -> dict:
    """
    Runs health checks for core services and updates SYSTEM_HEALTH.
    Returns a dictionary with the latest results.
    """
    results = {}

    # 1. ORACLE_ADW
    start = time.time()
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
        cursor.close()
        conn.close()

        latency_ms = int((time.time() - start) * 1000)
        _update_system_health("ORACLE_ADW", "ONLINE", latency_ms, None)
        results["ORACLE_ADW"] = {"status": "ONLINE", "latency_ms": latency_ms, "error": None}

    except Exception as e:
        _update_system_health("ORACLE_ADW", "OFFLINE", None, str(e))
        results["ORACLE_ADW"] = {"status": "OFFLINE", "latency_ms": None, "error": str(e)}

    # 2. OCI_GENAI
    start = time.time()
    try:
        # Keep this tiny so it acts like a ping
        response = oci_genai.get_chat_response("Health check. Reply with OK.")
        latency_ms = int((time.time() - start) * 1000)

        if response:
            _update_system_health("OCI_GENAI", "ONLINE", latency_ms, None)
            results["OCI_GENAI"] = {"status": "ONLINE", "latency_ms": latency_ms, "error": None}
        else:
            _update_system_health("OCI_GENAI", "OFFLINE", None, "Empty response from OCI_GENAI")
            results["OCI_GENAI"] = {"status": "OFFLINE", "latency_ms": None, "error": "Empty response from OCI_GENAI"}

    except Exception as e:
        _update_system_health("OCI_GENAI", "OFFLINE", None, str(e))
        results["OCI_GENAI"] = {"status": "OFFLINE", "latency_ms": None, "error": str(e)}

    # 3. DISCORD_BOT
    # Check if the process is actually running on this Mac
    try:
        import subprocess
        # Look for the discord bot script in the process list
        result = subprocess.run(
            ["pgrep", "-f", "discord_bot.py"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            _update_system_health("DISCORD_BOT", "ONLINE", 0, None)
            results["DISCORD_BOT"] = {"status": "ONLINE", "latency_ms": 0, "error": None}
        else:
            _update_system_health("DISCORD_BOT", "OFFLINE", None, "Discord bot process not running")
            results["DISCORD_BOT"] = {"status": "OFFLINE", "latency_ms": None, "error": "Discord bot process not running"}

    except Exception as e:
        _update_system_health("DISCORD_BOT", "OFFLINE", None, str(e))
        results["DISCORD_BOT"] = {"status": "OFFLINE", "latency_ms": None, "error": str(e)}

    # 4. VECTOR_SEARCH
    start = time.time()
    try:
        # NOTE:
        # Use the SAME vector dimension your DB expects.
        # If your vector index expects 768, keep 768 here.
        test_vector = [0.1] * 768

        database.search_kb_vectors(test_vector, n_results=1)

        latency_ms = int((time.time() - start) * 1000)
        _update_system_health("VECTOR_SEARCH", "ONLINE", latency_ms, None)
        results["VECTOR_SEARCH"] = {"status": "ONLINE", "latency_ms": latency_ms, "error": None}

    except Exception as e:
        _update_system_health("VECTOR_SEARCH", "OFFLINE", None, str(e))
        results["VECTOR_SEARCH"] = {"status": "OFFLINE", "latency_ms": None, "error": str(e)}

    return results


if __name__ == "__main__":
    output = perform_health_checks()
    print("\n SYSTEM HEALTH RESULTS ")
    for service, data in output.items():
        print(f"{service}: {data}")