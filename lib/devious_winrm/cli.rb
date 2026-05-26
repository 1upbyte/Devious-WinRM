# frozen_string_literal: true

require "optparse"
require "readline"
require_relative "kerberos"
require_relative "version"

module DeviousWinRM
  class ConnectionError < StandardError; end

  class CLI
    LM_HASH = "aad3b435b51404eeaad3b435b51404ee"

    def self.start(argv = ARGV)
      new(argv).run
    end

    def initialize(argv)
      @argv = argv
      @options = {
        port: 5985,
        kerberos: false
      }
    end

    def run
      parse!
      validate!
      prepare_kerberos
      connect
    rescue OptionParser::ParseError, ArgumentError, NotImplementedError, KerberosError, ConnectionError => e
      warn "[!] #{e.message}"
      exit 1
    rescue Interrupt
      puts "\nExiting."
      exit 130
    end

    private

    def parse!
      parser = OptionParser.new do |opts|
        opts.banner = "Usage: dwrm [options] HOST"
        opts.separator ""
        opts.separator "Options:"

        opts.on("-u", "--username USER", "Username used for authentication.") { |value| @options[:username] = value }
        opts.on("-p", "--password PASS", "Password used for authentication. Cannot be used with an NTLM hash.") { |value| @options[:password] = value }
        opts.on("-P", "--port PORT", Integer, "Port of remote host. Defaults to 5985.") { |value| @options[:port] = value }
        opts.on("-k", "--kerberos", "Use Kerberos authentication.") { @options[:kerberos] = true }
        opts.on("-H", "--hash HASH", "NTLM hash. Accepts LM:NTLM or NTLM.") { |value| @options[:nt_hash] = value }
        opts.on("--domain-controller DC", "--dc DC", "FQDN for the domain controller.") { |value| @options[:dc] = value }
        opts.on("-v", "--version", "Print version and exit.") do
          puts DeviousWinRM::VERSION
          exit 0
        end
        opts.on("-h", "--help", "Print help and exit.") do
          puts opts
          exit 0
        end
      end

      parser.parse!(@argv)
      @options[:host] = @argv.shift
      return if @options[:host]

      puts parser
      exit 1
    end

    def validate!
      if @options[:nt_hash]
        raise ArgumentError, "Password and NTLM hash cannot be used together." if @options[:password]

        @options[:nt_hash] = @options[:nt_hash].split(":").last
        unless @options[:nt_hash].match?(/\A[0-9a-fA-F]{32}\z/)
          raise ArgumentError, "NTLM hash must be 32 hexadecimal characters."
        end
      end

      unless @options[:kerberos]
        raise ArgumentError, "Only Kerberos connections are supported in the Ruby implementation. Pass -k."
      end

      dc = @options[:dc] || @options[:host]
      if dc.count(".") < 2
        raise ArgumentError, "Domain controller or host FQDN must be specified when using Kerberos."
      end

      @options[:dc] = dc
    end

    def prepare_kerberos
      @kerberos = Kerberos.new(
        dc: @options[:dc],
        username: @options[:username],
        password: @options[:password],
        nt_hash: @options[:nt_hash]
      )
      @kerberos.prepare
    end

    def connect
      with_suppressed_warnings do
        require "winrm"

        endpoint = "http://#{@options[:host]}:#{@options[:port]}/wsman"
        connection = WinRM::Connection.new(
          endpoint: endpoint,
          transport: :kerberos,
          realm: @kerberos.realm,
          service: "HTTP",
          user: @options[:username] || "kerberos",
          password: @options[:password] || "kerberos",
          operation_timeout: 500,
          receive_timeout: 510
        )

        puts "[*] Devious-WinRM v#{DeviousWinRM::VERSION}"
        puts "[*] Connecting to #{@options[:host]} using Kerberos realm #{@kerberos.realm}"

        connection.shell(:powershell) do |shell|
          shell.run("$PSVersionTable.PSVersion.ToString()") do |stdout, stderr|
            write_streams(stdout, stderr)
          end
          repl(shell)
        end
      end
    rescue WinRM::WinRMAuthorizationError => e
      raise ConnectionError, "Authentication failed: #{short_error(e.message)}"
    rescue WinRM::WinRMHTTPTransportError, HTTPClient::TimeoutError, SocketError, Errno::ECONNREFUSED => e
      raise ConnectionError, "Connection error: #{short_error(e.message)}"
    rescue GSSAPI::GssApiError => e
      raise ConnectionError, "Kerberos authentication failed: #{short_error(e.message)}"
    end

    def repl(shell)
      configure_completion(shell)

      loop do
        line = read_command(prompt(shell))
        break unless line

        command = line.strip
        next if command.empty?
        break if %w[exit quit].include?(command.downcase)

        run_interactive_command(shell, line)
      end
    rescue Interrupt
      puts
      retry
    ensure
      Readline.completion_proc = nil if STDIN.tty?
    end

    def run_interactive_command(shell, line)
      shell.run(line) do |stdout, stderr|
        write_streams(stdout, stderr)
      end
    rescue Interrupt
      puts "\n[*] Aborting command."
    end

    def write_streams(stdout, stderr)
      print stdout if stdout && !stdout.empty?
      $stderr.write stderr if stderr && !stderr.empty?
    end

    def read_command(prompt)
      return Readline.readline(prompt, true) if STDIN.tty?

      print prompt
      STDIN.gets&.chomp
    end

    def prompt(shell)
      "#{current_path(shell)}> "
    end

    def current_path(shell)
      output = run_remote(shell, "Get-Location | Select-Object -ExpandProperty Path")
      output.strip.empty? ? "PS #{@options[:host]}" : output.strip
    rescue ConnectionError
      "PS #{@options[:host]}"
    end

    def configure_completion(shell)
      return unless STDIN.tty?

      completer = RemotePathCompleter.new(shell)
      Readline.completion_append_character = nil
      Readline.basic_word_break_characters = " \t\n`@$><=;|&{("
      Readline.completion_proc = proc { |word| completer.complete(word, Readline.line_buffer.to_s) }
    end

    def run_remote(shell, command)
      stdout_text = +""
      stderr_text = +""

      shell.run(command) do |stdout, stderr|
        stdout_text << stdout if stdout
        stderr_text << stderr if stderr
      end

      raise ConnectionError, stderr_text.strip unless stderr_text.strip.empty?

      stdout_text
    end

    def with_suppressed_warnings
      Warning[:deprecated] = false if Warning.respond_to?(:[]=)
      verbose = $VERBOSE
      $VERBOSE = nil
      yield
    ensure
      $VERBOSE = verbose
    end

    def short_error(message)
      message.to_s.lines.map(&:strip).reject(&:empty?).first || "unknown error"
    end
  end

  class RemotePathCompleter
    def initialize(shell)
      @shell = shell
    end

    def complete(word, line_buffer)
      token = current_token(word, line_buffer)
      query = parse_query(token)
      children = remote_children(query, directory_only?(line_buffer))

      children.map do |child|
        build_completion(token, query, child)
      end
    rescue StandardError
      []
    end

    private

    def current_token(word, line_buffer)
      buffer = line_buffer[0...Readline.point].to_s
      token_start = 0
      quote = nil

      buffer.each_char.with_index do |char, index|
        if quote
          quote = nil if char == quote
        elsif char == "\"" || char == "'"
          quote = char
        elsif char.match?(/\s/)
          token_start = index + 1
        end
      end

      token = buffer[token_start..].to_s
      token.empty? ? word.to_s : token
    end

    def parse_query(token)
      quote = token.start_with?("\"", "'") ? token[0] : nil
      path_token = quote ? token[1..].to_s : token
      normalized = path_token.tr("/", "\\")
      ended_with_slash = normalized.end_with?("\\")
      directory, prefix = split_path(normalized)

      if ended_with_slash
        directory = join_path(directory, prefix)
        prefix = ""
      end

      drive_root = directory.match?(/\A[A-Za-z]:\z/)
      directory += "\\" if drive_root

      {
        token: token,
        path_token: path_token,
        quote: quote,
        directory: directory.empty? ? "." : directory,
        prefix: prefix,
        drive_root: drive_root
      }
    end

    def split_path(path)
      separator = path.rindex("\\")
      return [".", path] unless separator

      directory = path[0...separator]
      prefix = path[(separator + 1)..] || ""
      directory = "\\" if directory.empty? && path.start_with?("\\")
      [directory, prefix]
    end

    def join_path(directory, child)
      return child if directory == "."
      return "#{directory}#{child}" if directory.end_with?("\\")

      "#{directory}\\#{child}"
    end

    def directory_only?(line_buffer)
      line_buffer.strip.split(/\s+/, 2).first.to_s.casecmp("cd").zero?
    end

    def remote_children(query, directory_only)
      attrs = directory_only ? "-Attributes Directory" : ""
      command = <<~POWERSHELL
        Get-ChildItem -LiteralPath '#{escape_single_quoted(query[:directory])}' -Filter '#{escape_single_quoted(query[:prefix])}*' #{attrs} -Force |
          Select-Object @{Name='Name'; Expression={if ($_.PSIsContainer) {$_.Name + '\\'} else {$_.Name}}} |
          Select-Object -ExpandProperty Name
      POWERSHELL

      output = +""
      @shell.run(command) do |stdout, stderr|
        output << stdout if stdout
      end

      output.lines.map(&:strip).reject(&:empty?)
    end

    def escape_single_quoted(value)
      value.to_s.gsub("'", "''")
    end

    def build_completion(token, query, child)
      child = "" if child == query[:directory]
      child = child.delete_suffix("\\")
      child = "\\#{child}" if query[:drive_root]

      completion = token_prefix(query[:path_token], query[:prefix]) + child
      quote_completion(completion, query[:quote])
    end

    def token_prefix(token, prefix)
      return token if prefix.empty? && token.end_with?("\\", "/")
      return "" if prefix.empty?

      token[0...(token.length - prefix.length)] || ""
    end

    def quote_completion(completion, quote)
      if quote
        return %(#{quote}#{completion.gsub(quote, "`#{quote}")}#{quote})
      end

      return completion unless completion.match?(/\s/)

      %("#{completion.gsub('"', '\\"')}")
    end
  end
end
