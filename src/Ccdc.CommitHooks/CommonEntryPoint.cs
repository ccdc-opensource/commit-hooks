using System;

namespace Ccdc.CommitHooks
{
    public class CommonEntryPoint
    {
        public CommonEntryPoint(string[] args)
        {
            // Read args: is this running under github actions or not?

            // Read args: what kind of commit hook this is:
            // Full list is available at
            // https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks

            // Instantiate CommitHookCheckInterface classes
        }

        public int main()
        {
            // run CommitHookCheckInterface checks
            // return 0 if everything is ok
            // or 1 if something should be aborted
            return 0;
        }
    }
}
