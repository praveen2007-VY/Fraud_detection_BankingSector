import java.io.*;
import java.net.*;
public class WriteHostsFile {
    public static void main(String[] args) throws Exception {
        // Get hostname WITHOUT resolving (just the name part)
        String localHostname;
        try {
            localHostname = InetAddress.getLocalHost().getHostName();
        } catch (UnknownHostException e) {
            // If we can't resolve, extract hostname from exception message
            String msg = e.getMessage();
            // The message is like "hostname: No such host..."
            localHostname = msg.split(":")[0].trim();
        }
        System.out.println("Java hostname: [" + localHostname + "] len=" + localHostname.length());
        for (int i = 0; i < localHostname.length(); i++) {
            System.out.println("  char[" + i + "]: " + (int)localHostname.charAt(i) + " (0x" + Integer.toHexString(localHostname.charAt(i)) + ")");
        }
        // Write hosts file in UTF-8
        String hostsPath = args[0];
        try (OutputStreamWriter w = new OutputStreamWriter(new FileOutputStream(hostsPath), java.nio.charset.StandardCharsets.UTF_8)) {
            w.write("127.0.0.1   localhost\n");
            w.write("::1         localhost\n");
            w.write("127.0.0.1   " + localHostname + "\n");
            w.write("127.0.0.1   Prvn??\n");
            w.write("127.0.0.1   Prvn?\n");
            w.write("127.0.0.1   PRVN??\n");
            w.write("127.0.0.1   PRVN?\n");
        }
        System.out.println("Wrote hosts file: " + hostsPath);
    }
}
