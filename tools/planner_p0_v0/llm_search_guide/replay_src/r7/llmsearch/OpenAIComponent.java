package r7.llmsearch;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import com.fasterxml.jackson.databind.ObjectMapper;
import reactor.core.publisher.Mono;

/**
 * Offline transport shim for the upstream P0 Sabre jar.
 *
 * Put this class before lib/sabre.jar on the classpath. It replays only the
 * published Gramma transcript and fails closed for embeddings or extra calls.
 * It never opens a network connection and is not a live-model test.
 */
public final class OpenAIComponent {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String FIRST_SUFFIX =
            "List two different actions that could happen first. State each as a short sentence (e.g. 5-10 words) on its own line. ";
    private static final String NEXT_SUFFIX =
            "List two different actions that could happen next. State each as a short sentence (e.g. 5-10 words) on its own line. ";
    private static final String STORY_PREFIX = "The story begins with the following steps:\\n";
    private static final String GOAL_PREFIX = "The story must end with ";

    private final List<Turn> turns;
    private int cursor;

    public OpenAIComponent() {
        String transcript = System.getProperty("p0.replay.transcript", "out/run_1/transcript.txt");
        try {
            this.turns = readTurns(Path.of(transcript));
        } catch (IOException e) {
            throw new IllegalStateException("Cannot read replay transcript: " + transcript, e);
        }
    }

    public void setChatModel(String ignored) {}
    public void setSystemRole(String ignored) {}

    public Mono<String> completeChat(String[] messages, int maxTokens, float temperature) {
        if (messages == null || messages.length != 1)
            return Mono.error(new IllegalStateException("Replay expects exactly one user message"));
        if (cursor >= turns.size())
            return Mono.error(new IllegalStateException("Replay exhausted after " + cursor + " turns"));

        Turn turn = turns.get(cursor);
        if (turn.expectedPrompt == null || !turn.expectedPrompt.equals(messages[0])) {
            int mismatch = firstMismatch(turn.expectedPrompt, messages[0]);
            return Mono.error(new IllegalStateException("Replay prompt mismatch at turn " + cursor
                    + " (expectedChars=" + turn.expectedPrompt.length()
                    + ", actualChars=" + messages[0].length()
                    + ", firstMismatch=" + mismatch + ")"));
        }

        try {
            String content = String.join("\n", turn.suggestions);
            String response = JSON.writeValueAsString(java.util.Map.of(
                    "choices", List.of(java.util.Map.of(
                            "message", java.util.Map.of("content", content)))));
            cursor++;
            System.err.println("P0_REPLAY turn=" + cursor + " source=out/run_1/transcript.txt");
            return Mono.just(response);
        } catch (Exception e) {
            return Mono.error(new IllegalStateException("Could not encode replay response", e));
        }
    }

    public Mono<String> getTextEmbedding(String prompt) {
        return Mono.error(new IllegalStateException(
                "P0_REPLAY has no live embedding transport; exact cached vectors must satisfy every request"));
    }

    private static List<Turn> readTurns(Path path) throws IOException {
        List<String> lines = Files.readAllLines(path);
        List<Turn> turns = new ArrayList<>();
        String rootPrompt = null;
        for (int i = 0; i < lines.size();) {
            String line = lines.get(i);
            if (line.equals("PROMPT:")) {
                StringBuilder prompt = new StringBuilder();
                i++;
                while (i < lines.size() && !lines.get(i).equals("SUGGESTIONS:")
                        && !lines.get(i).isBlank()) {
                    if (!prompt.isEmpty()) prompt.append('\n');
                    prompt.append(lines.get(i++));
                }
                rootPrompt = prompt.toString();
                turns.add(new Turn(rootPrompt, readSuggestions(lines, i)));
                i = afterActionCosts(lines, i);
                continue;
            }
            if (line.startsWith("[PROMPT]... ")) {
                List<String> actions = new ArrayList<>();
                i++;
                while (i < lines.size() && !lines.get(i).startsWith("List two different actions")) {
                    if (!lines.get(i).isBlank()) actions.add(lines.get(i));
                    i++;
                }
                if (i >= lines.size() || rootPrompt == null)
                    throw new IOException("Malformed transcript prompt block");
                String goal = extractGoal(rootPrompt);
                String base = rootPrompt.substring(0, rootPrompt.indexOf(GOAL_PREFIX));
                StringBuilder expected = new StringBuilder(base).append(STORY_PREFIX);
                for (String action : actions) expected.append(action).append("\\n");
                expected.append(goal).append(NEXT_SUFFIX);
                turns.add(new Turn(expected.toString(), readSuggestions(lines, i + 1)));
                i = afterActionCosts(lines, i + 1);
                continue;
            }
            i++;
        }
        if (turns.isEmpty()) throw new IOException("No replay turns found in " + path);
        return turns;
    }

    private static String extractGoal(String rootPrompt) throws IOException {
        int start = rootPrompt.indexOf(GOAL_PREFIX);
        int end = rootPrompt.lastIndexOf(FIRST_SUFFIX);
        if (start < 0 || end < start) throw new IOException("Cannot locate root goal/prompt boundary");
        return rootPrompt.substring(start, end);
    }

    private static List<String> readSuggestions(List<String> lines, int markerIndex) throws IOException {
        while (markerIndex < lines.size() && lines.get(markerIndex).isBlank()) markerIndex++;
        if (markerIndex >= lines.size() || !lines.get(markerIndex).equals("SUGGESTIONS:"))
            throw new IOException("Expected SUGGESTIONS marker");
        List<String> suggestions = new ArrayList<>();
        for (int i = markerIndex + 1; i < lines.size(); i++) {
            if (lines.get(i).equals("ACTION COSTS:") || lines.get(i).isBlank()) break;
            suggestions.add(lines.get(i));
        }
        if (suggestions.isEmpty()) throw new IOException("Empty replay suggestion set");
        return suggestions;
    }

    private static int afterActionCosts(List<String> lines, int from) {
        for (int i = from; i < lines.size(); i++) {
            if (lines.get(i).equals("ACTION COSTS:")) {
                int next = i + 1;
                while (next < lines.size() && !lines.get(next).isBlank()) next++;
                return next;
            }
        }
        return lines.size();
    }

    private static int firstMismatch(String expected, String actual) {
        int limit = Math.min(expected.length(), actual.length());
        for (int i = 0; i < limit; i++) if (expected.charAt(i) != actual.charAt(i)) return i;
        return expected.length() == actual.length() ? -1 : limit;
    }

    private record Turn(String expectedPrompt, List<String> suggestions) {}
}
