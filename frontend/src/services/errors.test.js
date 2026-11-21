// Unit tests for the browser-side network/error translation. Run with: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { errMsg, isNetworkFailure, NETWORK_MESSAGE, TIMEOUT_MESSAGE } from "./errors.js";

test("no response at all (server unreachable) gives the network message", () => {
  assert.equal(errMsg({ message: "Network Error", code: "ERR_NETWORK" }), NETWORK_MESSAGE);
});

test("a timeout gives the timeout message", () => {
  assert.equal(errMsg({ code: "ECONNABORTED" }), TIMEOUT_MESSAGE);
});

test("Vite proxy answering 500 with an empty body (back end stopped) is a network failure", () => {
  const e = { response: { status: 500, data: "" } };
  assert.equal(isNetworkFailure(e), true);
  assert.equal(errMsg(e), NETWORK_MESSAGE);
});

test("502, 503 and 504 from a gateway without a JSON body are network failures", () => {
  for (const status of [502, 503, 504]) {
    assert.equal(errMsg({ response: { status, data: "<html>Bad gateway</html>" } }), NETWORK_MESSAGE);
  }
});

test("the API's own 503 DATABASE_ERROR keeps its message", () => {
  const e = { response: { status: 503, data: { detail: "The database is temporarily unavailable. Please try again.", code: "DATABASE_ERROR" } } };
  assert.equal(isNetworkFailure(e), false);
  assert.equal(errMsg(e), "The database is temporarily unavailable. Please try again.");
});

test("validation errors list each field message", () => {
  const e = { response: { status: 422, data: { detail: "title: too short", code: "VALIDATION_ERROR", errors: [{ field: "title", message: "String should have at least 5 characters" }] } } };
  assert.equal(errMsg(e), "title: too short String should have at least 5 characters");
});

test("a 4xx without a JSON body falls back to the status code", () => {
  assert.equal(errMsg({ response: { status: 404, data: "" } }), "Request failed (404).");
});

test("a missing error object is handled", () => {
  assert.equal(errMsg(undefined), "Something went wrong.");
});
