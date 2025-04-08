import socket
import psutil
import os
import sys

def check_port(port):
    """Check if a port is in use and by which process"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    
    if result == 0:
        # Port is in use, find which process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        return True, proc.info
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return True, None
    return False, None

def find_free_port(start_port=8000, end_port=9000):
    """Find a free port in the given range"""
    for port in range(start_port, end_port):
        in_use, _ = check_port(port)
        if not in_use:
            return port
    return None

def main():
    # Check specific ports
    ports_to_check = [8080, 8081, 5000]
    
    print("\n=== PORT STATUS ===")
    for port in ports_to_check:
        in_use, proc_info = check_port(port)
        if in_use:
            proc_details = f" - Used by: {proc_info}" if proc_info else " - Used by unknown process"
            print(f"🔴 Port {port} is IN USE{proc_details}")
        else:
            print(f"🟢 Port {port} is AVAILABLE")
            
    # Find a free port
    free_port = find_free_port()
    if free_port:
        print(f"\n✅ RECOMMENDED: Use port {free_port} for your Flask app")
        print(f"   To start server: python app.py {free_port}")
    else:
        print("\n❌ No free ports found in range 8000-9000")
        
    print("\n=== RUNNING PYTHON PROCESSES ===")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else 'Unknown'
                print(f"PID {proc.info['pid']}: {cmdline}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    print("\nTo kill a specific process: kill -9 PID")
    print("To kill all Flask instances: pkill -9 -f flask")

if __name__ == "__main__":
    main() 