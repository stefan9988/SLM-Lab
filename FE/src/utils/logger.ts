const isDev = import.meta.env.DEV;

type LogFn = (...args: unknown[]) => void;

interface Logger {
  debug: LogFn;
  info: LogFn;
  warn: LogFn;
  error: LogFn;
}

const noop: LogFn = () => {};

const logger: Logger = {
  debug: isDev ? console.debug.bind(console) : noop,
  info: isDev ? console.log.bind(console) : noop,
  warn: console.warn.bind(console),
  error: console.error.bind(console),
};

export default logger;
