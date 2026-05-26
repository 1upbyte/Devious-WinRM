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
        raise ArgumentError, "NTLM hash must be 32 characters long." unless @options[:nt_hash].length == 32
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
    rescue WinRM::WinRMAuthorizationError
      raise ConnectionError, "Authentication failed. Please check your credentials and Kerberos ticket."
    rescue WinRM::WinRMHTTPTransportError, HTTPClient::TimeoutError, SocketError, Errno::ECONNREFUSED => e
      raise ConnectionError, "Connection error: #{e.message}"
    end

    def repl(shell)
      prompt = "PS #{@options[:host]}> "

      while (line = read_command(prompt))
        command = line.strip
        next if command.empty?
        break if %w[exit quit].include?(command.downcase)

        shell.run(line) do |stdout, stderr|
          write_streams(stdout, stderr)
        end
      end
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

    def with_suppressed_warnings
      Warning[:deprecated] = false if Warning.respond_to?(:[]=)
      verbose = $VERBOSE
      $VERBOSE = nil
      yield
    ensure
      $VERBOSE = verbose
    end
  end
end
