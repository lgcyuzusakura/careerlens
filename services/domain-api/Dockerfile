ARG MAVEN_IMAGE=m.daocloud.io/docker.io/library/maven:3.9.11-eclipse-temurin-21
ARG JRE_IMAGE=m.daocloud.io/docker.io/library/eclipse-temurin:21.0.9_10-jre-alpine
FROM ${MAVEN_IMAGE} AS build
WORKDIR /workspace
COPY services/domain-api/pom.xml services/domain-api/settings.xml ./
RUN mvn -B -s settings.xml dependency:go-offline -q
COPY services/domain-api/src src
RUN mvn -B -s settings.xml verify -q
FROM ${JRE_IMAGE} AS runtime
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build /workspace/target/domain-api-0.1.0.jar app.jar
USER app
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s CMD wget -q -O /dev/null http://127.0.0.1:8080/actuator/health/readiness || exit 1
ENTRYPOINT ["java","-XX:MaxRAMPercentage=70","-jar","app.jar"]
