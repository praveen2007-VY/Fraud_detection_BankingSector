import os
import sys

# Set Java options BEFORE importing pyflink so the gateway JVM inherits it
conf_dir = os.path.join(os.path.dirname(__file__), "conf")
jvm_hosts = os.path.join(conf_dir, "jvm-hosts").replace("\\", "/")

os.environ["FLINK_CONF_DIR"] = conf_dir
os.environ["_JAVA_OPTIONS"] = (
    "--add-opens java.base/java.util=ALL-UNNAMED "
    "--add-opens java.base/java.lang=ALL-UNNAMED "
    "--add-opens java.base/java.lang.reflect=ALL-UNNAMED "
    "--add-opens java.base/java.io=ALL-UNNAMED "
    f"-Djdk.net.hosts.file={jvm_hosts} "
    "-Dfile.encoding=UTF-8 "
    "-Dstdout.encoding=UTF-8 "
    "-Djava.net.preferIPv4Stack=true "
    "-Djava.rmi.server.hostname=127.0.0.1"
)

from pyflink.datastream import StreamExecutionEnvironment

def run_smoke_test():
    print("Testing PyFlink imports...")
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    print("Creating simple collection data stream...")
    ds = env.from_collection([1, 2, 3, 4, 5])
    
    print("Applying simple map transformation...")
    doubled = ds.map(lambda x: x * 2)
    
    print("Adding print sink...")
    doubled.print()
    
    print("Executing job...")
    env.execute("smoke_test")
    print("Smoke test completed successfully!")

if __name__ == "__main__":
    run_smoke_test()
