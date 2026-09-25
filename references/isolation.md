# Open Reading isolation

Open Reading consumes only a paper bundle (`source/paper.pdf`, supplied supplements, source map and skill resources). Project documents, repositories, chats, goals, memory and connector lookups are forbidden until `/paper-apply`. Implementations should create a source-only working directory and pass only that directory to an isolated worker. Any discovered project context invalidates the read and requires restart.
