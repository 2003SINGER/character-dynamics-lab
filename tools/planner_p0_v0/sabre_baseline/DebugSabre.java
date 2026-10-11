import edu.uky.cs.nil.sabre.Session;
import java.io.File;

/** Diagnostic adapter: expose exceptions hidden by Sabre Main's CLI catch. */
public final class DebugSabre {
    public static void main(String[] args) {
        try {
            Session session = new Session();
            session.setProblem(new File(args[0]));
            System.err.println("PARSED");
            session.getCompiledProblem();
            System.err.println("COMPILED");
            session.setSearchLimit(200);
            session.setTimeLimit(20_000);
            System.out.println(session.getPrinter().toString(session.getResult()));
        } catch (Throwable error) {
            System.err.println("DIAGNOSTIC_EXCEPTION " + error.getClass().getName()
                    + ": " + error.getMessage());
            StackTraceElement[] trace = error.getStackTrace();
            int count = Math.min(trace.length, 40);
            for (int i = 0; i < count; i++) {
                System.err.println("  at " + trace[i]);
            }
            if (trace.length > count) {
                System.err.println("  ... " + (trace.length - count) + " more frames");
            }
            Throwable cause = error.getCause();
            if (cause != null && cause != error) {
                System.err.println("CAUSE " + cause.getClass().getName()
                        + ": " + cause.getMessage());
                StackTraceElement[] causeTrace = cause.getStackTrace();
                for (int i = 0; i < Math.min(causeTrace.length, 12); i++) {
                    System.err.println("  caused by " + causeTrace[i]);
                }
            }
            System.exit(2);
        }
    }
}
