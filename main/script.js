const progress = document.querySelector(".progress-bar");
const progressLabelLeft = document.querySelector(".progress-label.left");
const progressLabelRight = document.querySelector(".progress-label.right");

// Milestones and current target selection
const MILESTONES = [50, 75, 100];
let activeMilestoneIndex = 0; // start with first milestone (50)
let totalCompletionsYesCount = 0;

function changeWidth() {
  const target = MILESTONES[activeMilestoneIndex];
  const pct = Math.min(100, Math.floor((totalCompletionsYesCount / target) * 100));
  progress.style.width = `${pct}%`;
  progressLabelLeft.innerHTML = `${pct}% completed`;
  progressLabelRight.innerHTML = `${totalCompletionsYesCount}/${target}`;
}

// Generic numeric comparator helper
function numericCompareFactory(keyFn) {
  return (a, b) => {
    const av = parseInt(keyFn(a) || 0, 10) || 0;
    const bv = parseInt(keyFn(b) || 0, 10) || 0;
    if (av > bv) return -1;
    if (av < bv) return 1;
    return 0;
  };
}

// Default comparator: total courses completed
// Default comparator: use computed total (skill badges + arcade games)
let currentComparator = numericCompareFactory((r) => {
  const s = parseInt(r['# of Skill Badges Completed'] || 0, 10) || 0;
  const a = parseInt(r['# of Arcade Games Completed'] || 0, 10) || 0;
  return s + a;
});

const updateData = async (filter, flag, bustCache = false) => {
  // Trigger refresh on the backend first if bustCache is true
  if (bustCache) {
    try {
      await fetch('https://gdg-google-cloud-study-jams-2025-pgcc.onrender.com/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  }
  
  // Add cache-busting parameter if needed
  const cacheBuster = bustCache ? `?t=${Date.now()}` : '';
  const serverUrl = 'https://gdg-google-cloud-study-jams-2025-pgcc.onrender.com';
  let data = await (await fetch(`${serverUrl}/data${cacheBuster}`)).json();
  
  // Get last modified time from data.json
  try {
    const response = await fetch(`${serverUrl}/data${cacheBuster}`);
    const lastModified = response.headers.get('Last-Modified');
    const lastUpdateEl = document.getElementById('last-update-text');
    
    if (lastModified && lastUpdateEl) {
      const date = new Date(lastModified);
      const formattedDate = date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
      lastUpdateEl.textContent = `📊 Last updated: ${formattedDate} • Click "Refresh Data" to update now!`;
    } else if (lastUpdateEl) {
      // Fallback: show current time if Last-Modified header is not available
      const now = new Date();
      const formattedDate = now.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
      lastUpdateEl.textContent = `📊 Last updated: ${formattedDate} • Click "Refresh Data" to update now!`;
    }
  } catch (e) {
    console.error('Could not fetch last modified time:', e);
  }
  
  if (filter !== "") {
    data = data.filter((el) => {
      return el["User Name"] && el["User Name"].toLowerCase().includes(filter.toLowerCase());
    });
  }

  data.sort(currentComparator);

  // Reset counter each time we render
  totalCompletionsYesCount = 0;

  // Reset milestone if previous was achieved
  if (activeMilestoneIndex < MILESTONES.length - 1 && totalCompletionsYesCount >= MILESTONES[activeMilestoneIndex]) {
    activeMilestoneIndex++;
  }

  let html = "";

  const truncate = (s, n = 60) => {
    if (!s) return '';
    return s.length > n ? `<span title="${s}">${s.slice(0,n)}...` + `</span>` : s;
  };

  data.forEach((d, i) => {
    // Safe reads for preserved columns
    const redemption = d['Access Code Redemption Status'] || d['Campaign Code Redemption Status'] || '';
    const allSkill = d['All Skill Badges & Games Completed'] || d['All 3 Pathways Completed - Yes or No'] || '';
    const badgesCount = d['# of Skill Badges Completed'] || 0;
    const badgesNames = d['Names of Completed Skill Badges'] || '';
    const arcadeCount = d['# of Arcade Games Completed'] || 0;
    const arcadeNames = d['Names of Completed Arcade Games'] || '';

    // Determine completion according to new rule: at least 19 skill badges and >=1 arcade game
    const badgesNumeric = parseInt(badgesCount, 10) || 0;
    const arcadeNumeric = parseInt(arcadeCount, 10) || 0;
    const completedByRule = badgesNumeric >= 19 && arcadeNumeric >= 1;

    if (completedByRule) {
      totalCompletionsYesCount++;
    }

    // Determine row styling with Tailwind classes
    let rowClass = 'hover:bg-gray-50 transition-colors';
    if (allSkill === 'Yes') {
      rowClass = 'bg-green-100 hover:bg-green-200 transition-colors';
    } else if (redemption === 'No') {
      rowClass = 'bg-red-100 hover:bg-red-200 transition-colors';
    }

    html += `<tr class="${rowClass}">
                  <td class="px-4 py-3 text-center font-medium text-gray-700">${i + 1}</td>
                  <td class="px-4 py-3"><a href="${d["Google Cloud Skills Boost Profile URL"] || '#'}" target="_blank" class="text-blue-600 hover:text-blue-800 font-medium hover:underline">${d["User Name"] || ''}</a></td>
                  <td class="px-4 py-3 text-center text-sm">${redemption}</td>
                  <td class="px-4 py-3 text-center text-sm font-semibold ${allSkill === 'Yes' ? 'text-green-600' : 'text-gray-600'}">${allSkill}</td>
                  <td class="px-4 py-3 text-center font-semibold text-blue-600">${badgesCount}</td>
                  <td class="px-4 py-3 text-sm text-gray-600">${truncate(badgesNames)}</td>
                  <td class="px-4 py-3 text-center font-semibold text-purple-600">${arcadeCount}</td>
                  <td class="px-4 py-3 text-sm text-gray-600">${truncate(arcadeNames)}</td>
                  <td class="px-4 py-3 text-center text-xl">${d["Gen AI Arcade Game Completion"] === "1" ? "💯" : "❌"}</td>
                  <td class="px-4 py-3 text-center font-bold text-lg text-gray-800">${(parseInt(badgesCount,10)||0) + (parseInt(arcadeCount,10)||0)}</td>
    </tr>`;
  });

  console.log("Completions (>=19 badges + >=1 arcade):", totalCompletionsYesCount);

  // After counting, auto-advance milestone while possible
  while (activeMilestoneIndex < MILESTONES.length - 1 && totalCompletionsYesCount >= MILESTONES[activeMilestoneIndex]) {
    activeMilestoneIndex++;
  }

  // Update milestone UI
  const milestoneLabelEl = document.getElementById('milestone-label');
  const milestoneStatusEl = document.getElementById('milestone-status');
  const activeTarget = MILESTONES[activeMilestoneIndex];
  if (milestoneLabelEl) milestoneLabelEl.textContent = `Active milestone: ${activeTarget}`;
  if (milestoneStatusEl) {
    if (totalCompletionsYesCount >= activeTarget) {
      milestoneStatusEl.textContent = `Reached ${activeTarget}!`;
    } else {
      milestoneStatusEl.textContent = `${totalCompletionsYesCount}/${activeTarget} completions`;
    }
  }

  if (flag) changeWidth();
  document.getElementById("gccp_body").innerHTML = html;
};

updateData("", true);
const input = document.getElementById("input");
input.addEventListener("input", () => {
  updateData(input.value, false);
});

// Wire the sort-select control
const sortSelect = document.getElementById('sort-select');
if (sortSelect) {
  sortSelect.addEventListener('change', () => {
    const val = sortSelect.value;
    if (val === 'courses') {
      currentComparator = numericCompareFactory((r) => r['# of Courses Completed']);
    } else if (val === 'totalBadges') {
      // sum of skill + arcade
      currentComparator = numericCompareFactory((r) => {
        const s = parseInt(r['# of Skill Badges Completed'] || 0, 10) || 0;
        const a = parseInt(r['# of Arcade Games Completed'] || 0, 10) || 0;
        return s + a;
      });
    } else if (val === 'skill') {
      currentComparator = numericCompareFactory((r) => r['# of Skill Badges Completed']);
    } else if (val === 'arcade') {
      currentComparator = numericCompareFactory((r) => r['# of Arcade Games Completed']);
    }
    // re-render with new sort
    updateData(input.value, false);
  });
}

// Refresh button handler
const refreshBtn = document.getElementById('refresh-btn');
const refreshStatus = document.getElementById('refresh-status');
const refreshIcon = document.getElementById('refresh-icon');
const refreshText = document.getElementById('refresh-text');

if (refreshBtn && refreshStatus && refreshIcon && refreshText) {
  refreshBtn.addEventListener('click', async () => {
    // Disable button and show loading state
    refreshBtn.disabled = true;
    refreshIcon.classList.add('spinner');
    refreshText.textContent = 'Refreshing...';
    
    // Show loading status with animation
    refreshStatus.innerHTML = '<div class="slide-in pulse">🔄 Fetching latest data from Google Cloud Skills Boost...</div>';
    refreshStatus.style.color = '#4285f4';
    
    try {
      const response = await fetch('https://gdg-google-cloud-study-jams-2025-pgcc.onrender.com/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Show success message
        refreshStatus.innerHTML = '<div class="slide-in">✅ Data refreshed successfully! Updating leaderboard...</div>';
        refreshStatus.style.color = '#0f9d58';
        
        // Reload the data from data.json with cache-busting
        setTimeout(() => {
          // Force fresh fetch with cache-busting
          updateData(input.value, true, true);
          
          // Update the last modified timestamp with animation
          const lastUpdateEl = document.getElementById('last-update-text');
          if (lastUpdateEl) {
            lastUpdateEl.classList.add('slide-in');
          }
          
          // Show final success message
          refreshStatus.innerHTML = '<div class="slide-in">🎉 Leaderboard updated with latest data!</div>';
          refreshStatus.style.color = '#0f9d58';
          
          // Clear status after 3 seconds
          setTimeout(() => {
            refreshStatus.innerHTML = '';
          }, 3000);
        }, 1500);
      } else {
        refreshStatus.innerHTML = `<div class="slide-in">❌ Refresh failed: ${result.error || 'Unknown error'}</div>`;
        refreshStatus.style.color = '#db4437';
        
        // Clear error after 5 seconds
        setTimeout(() => {
          refreshStatus.innerHTML = '';
        }, 5000);
      }
    } catch (error) {
      refreshStatus.innerHTML = '<div class="slide-in">❌ Could not connect to refresh server. Make sure it\'s running on port 5001!</div>';
      refreshStatus.style.color = '#db4437';
      console.error('Refresh error:', error);
      
      // Clear error after 5 seconds
      setTimeout(() => {
        refreshStatus.innerHTML = '';
      }, 5000);
    } finally {
      // Re-enable button and restore original state
      setTimeout(() => {
        refreshBtn.disabled = false;
        refreshIcon.classList.remove('spinner');
        refreshText.textContent = 'Refresh Data';
      }, 1500);
    }
  });
}
