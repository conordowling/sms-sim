# Running the simulation

0. Install Docker if needed. Ex. `brew install docker`
1. Start the stack: `docker compose up`. This starts up kafka and postgres, runs the migration and provisions the topic, starts the fleet of sender workers as well as the backend server and frontend app. Give it a minute for the stack to spin up before the frontend will be available.
2. Open up the [simulation monitor](localhost:3000). This is where you can see the results of the simulation as well as trigger the producer to queue up messages.
3. Click `Send Messages` to queue messages using the producer. The backend server will kick off an async process for the producer and senders will start to consume from the topic. The frontend polls every second by default to get the latest stats.
4. Watch the numbers tick up. You can queue up additional messages, but if you want to reset the simulation, you must `docker compose down` and then restart the stack which will start with a fresh table and topic.

## Configuring the simulation

- Number of messages can be configured using the field in the frontend.
- Number of senders can be configured using `SENDER_REPLICAS`.
- The refresh rate of the statistics can be configured using `REFRESH_INTERVAL_SECONDS`

For example:
```bash
SENDER_REPLICAS=5 REFRESH_INTERVAL_SECONDS=2 docker compose up
```
## Test Suite

If you just want to run the test suite:

```bash
uv run pytest
```

# AI Disclosure

I first hand-wrote a skeleton of the architecture including interfaces and tech stack and then used Claude Sonnet to fill in the implementation details. I then manually edited the AI generated code and added comments for readability. The frontend is entirely written using AI code generation.

# Architecture Design

Tech stack uses Python for the backend and message processing, React for the frontend, Kafka for the message queue, and PostgreSQL as the database. It uses Docker to orchestrate all the services locally.

The goal of the architecture is to enable horizontal scaling of both producers and senders while maintaining reliability and performance.

## Python

I've used python here with async patterns. It's not the most performant language, but suffices for this exercise. 

The use case is primarily I/O bound waiting for a response from the SMS provider API (sleeping).

## Kafka

I used Kafka as my message broker for scalability and reliability in a distributed system. We can scale the number of partitions to allow for horizontal scaling of consumers to achieve the desired throughput.

We can also use its retention policy to replay data in case of an outage and manually commit offsets to guarantee at-least-once semantics.

One limitation is that we can only have as many consumers as we have kafka partitions so in order to scale horizontally beyond the number of partitions, each consumer fetches a batch of messages that need to be sent and then processes them in parallel using asyncio.
We use a semaphore to limit the number of concurrent tasks.

## PostgreSQL

I've used PostgreSQL to track the outcomes of all the messages, whether they succeeded or failed and the time it took to send.

This is admittedly a bit overkill for this use case where simple counters would suffice. I definitely could have just used Redis to count the
number of successes, failures, and total send time and work out the average from those aggregates. This would accomplish the exact product requirements more performantly but sacrifice extensibility.

Storing the data in PostgreSQL instead allows for more complex analytical questions to be asked of the data such the throughput of the system over the course of the simulation down to second granularity.
One reason to prefer PostgreSQL over other database technologies is the support for both structured schemas as well as unstructured data using the JSON column type. It is also better suited for analytical workloads than MySQL.

If the scale of the data grew, a hybrid approach could be beneficial to answer common questions performantly, but store all the data necessary to ask other questions of the data.