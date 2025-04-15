from prompt_toolkit import PromptSession
import psrp
from psrp import WSManInfo
import typer


class Terminal:
    def __init__(self, conn: WSManInfo):
        ''' Initialize the terminal with a connection object.'''
        self.session = PromptSession()
        self.conn = conn

    def run(self):
        with psrp.SyncRunspacePool(self.conn) as rp:
            ps = psrp.SyncPowerShell(rp)
            error_count: int = 0
            while True:
                try:
                    # Get current directory
                    current_dir = ps.add_script('pwd').invoke()
                    # print(f"Current Directory: {current_dir[0]}")
                    user_input = self.session.prompt(str(current_dir[0]) + "> ")
                    ps.add_script(user_input)
                  
                    try:
                        out = ps.invoke()

                        had_error: bool = len(ps.streams.error) > error_count

                        if had_error:
                            print(ps.streams.error[-1])
                            error_count = len(ps.streams.error)
                        print()
                        for line in out:
                            print(line)
                    except Exception as e:
                        print(e)
                    finally:
                        ps._pipeline.metadata.commands = []
                except (KeyboardInterrupt, EOFError):
                    print('Goodbye!')
                    break



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