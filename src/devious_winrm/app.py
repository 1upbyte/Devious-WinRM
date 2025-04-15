from prompt_toolkit import PromptSession
import psrp
from psrp import WSManInfo
import typer


class Terminal:
    def __init__(self, conn: WSManInfo):
        ''' Initialize the terminal with a connection object.'''
        self.session = PromptSession()
        self.conn = conn
        self.error_count: int = 0

    def run(self):
        with psrp.SyncRunspacePool(self.conn) as rp:
            self.ps = psrp.SyncPowerShell(rp)
            while True:
                try:
                    current_dir = self.ps.add_script('pwd').invoke()
                    user_input = self.session.prompt(str(current_dir[0]) + "> ")
                   
                    if user_input == 'exit':
                        raise SystemExit                  
                    
                    try:
                        self.run_command(user_input)
                    except Exception as e:
                        print(e)
                    finally:
                        print()
                        self.ps._pipeline.metadata.commands = []
                except (KeyboardInterrupt, EOFError, SystemExit):
                    print('Goodbye!')
                    self.ps.close()
                    break
                except Exception as e:
                    print(e)
                    break
    
    def run_command(self, command: str):
        ''' Run a command in the terminal and print the output '''
        self.ps.add_script(command)
        self.ps.add_command('Out-String')
        out = self.ps.invoke()

        had_error: bool = len(self.ps.streams.error) > self.error_count
        if had_error:
            print(str(self.ps.streams.error[-1]).strip())
            self.error_count = len(self.ps.streams.error)
        if len(out[0]) > 0:
            print(out[0].strip())



def main(host, username: str, password: str, port: int = 5985, auth: str = 'ntlm'):
    ''' Main function to run the terminal '''
    conn = WSManInfo(
        server=host,
        username=username,
        password=password,
        port=port,
        auth=auth
    )
    terminal = Terminal(conn)
    terminal.run()

if __name__ == '__main__':
    typer.run(main)