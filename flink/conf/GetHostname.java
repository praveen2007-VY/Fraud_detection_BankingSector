public class GetHostname {
    public static void main(String[] args) throws Exception {
        String hostname = java.net.InetAddress.getLocalHost().getHostName();
        System.out.println("hostname_len=" + hostname.length());
        for (int i = 0; i < hostname.length(); i++) {
            System.out.println("char[" + i + "]=" + (int)hostname.charAt(i) + " hex=" + Integer.toHexString(hostname.charAt(i)));
        }
    }
}
