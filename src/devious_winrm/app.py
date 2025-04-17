from typing import Annotated
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
                    user_input: str = self.session.prompt(str(current_dir[0]) + "> ")
                   
                    if user_input.lower() == 'exit':
                        break               
                    try:
                        self.run_command(user_input)
                    except Exception as e:
                        print(e)
                        break
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


def main(host: Annotated[str, typer.Argument()],
        username: Annotated[str, typer.Option("-u", "--username")],
        password: Annotated[str, typer.Option("-p", "--password")] = None,
        port: Annotated[int, typer.Option("-P", "--port")] = 5985,
        auth: Annotated[str, typer.Option("-a", "--auth")] = "negotiate",
        nt_hash: Annotated[str, typer.Option("-H", "--hash")] = None):
    
    if password is None and nt_hash is None:
        raise ValueError("Either password or NTLM hash must be provided.")

    if nt_hash is not None:
        if len(nt_hash) != 32:
            raise ValueError("NTLM hash must be 32 characters long.")
        if password is not None:
            raise ValueError("Password and NTLM hash cannot be used together.")
        password = "aad3b435b51404eeaad3b435b51404ee:" + nt_hash 
    
    ''' Main function to run the terminal '''
    conn = WSManInfo(
        server=host,
        username=username,
        password=password,
        port=port,
        auth=auth
    )
    terminal = Terminal(conn)
    try:
        terminal.run()
    except Exception as e:
        print(e)
        typer.Exit()

if __name__ == '__main__':
    typer.run(main)