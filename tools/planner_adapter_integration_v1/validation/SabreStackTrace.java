package planner_adapter_integration_v1.validation;

import edu.uky.cs.nil.sabre.*;
import edu.uky.cs.nil.sabre.util.CommandLineArguments;
import java.io.File;

/** Temporary diagnostic entry point: preserve the pinned CLI arguments, expose swallowed stack traces. */
public final class SabreStackTrace {
    public static void main(String[] args) throws Exception {
        Session session = new Session();
        Main.configure(session, new CommandLineArguments(args), true);
        System.out.println(session.getResult());
    }
}
