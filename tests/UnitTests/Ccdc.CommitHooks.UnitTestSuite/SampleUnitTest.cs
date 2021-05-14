using System;
using Xunit;
using Ccdc.CommitHooks;

namespace Ccdc.CommitHooks.UnitTestSuite
{
    // This is using xUnit.net
    // https://xunit.net/docs/getting-started/netcore/cmdline
    public class SampleUnitTest
    {
        [Fact]
        public void Test1()
        {
            SampleCommitHookCheck c = new SampleCommitHookCheck();
            Assert.False(c.clientSideCheck());
            Assert.False(c.githubSideCheck());
        }
    }
}
