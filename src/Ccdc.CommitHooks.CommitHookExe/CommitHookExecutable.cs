using System;

namespace Ccdc.CommitHooks
{
    class CommitHookExecutable
    {
        static void Main(string[] args)
        {
            // Git commit hooks's return code is important
            CommonEntryPoint ep = new CommonEntryPoint(args);
            Environment.ExitCode = ep.main();
        }
    }
}
